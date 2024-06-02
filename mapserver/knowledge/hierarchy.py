#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-2024  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

import functools
import itertools
import json
from typing import cast, Iterator

#===============================================================================

import networkx as nx
import rdflib

#===============================================================================

from .rdf_utils import ILX_BASE, Node, Triple, Uri

#===============================================================================

NPO_ONTOLOGY = './ontologies/npo.ttl'
UBERON_ONTOLOGY = './ontologies/uberon-basic.json'

#===============================================================================

MULTICELLULAR_ORGANISM = Uri('UBERON:0000468')
ANATOMICAL_ROOT = MULTICELLULAR_ORGANISM

#===============================================================================

ILX_PART_OF = 'ILX:0112785'

IS_A = 'is_a'
PART_OF = Uri('BFO:0000050')

#===============================================================================

class IlxTerm:
    def __init__(self, result_row: rdflib.query.ResultRow):
        self.__uri = Uri(result_row.term)
        self.__label = result_row.get('label')
        self.__parents = []
        self.__have_ilx_parents = False

    def add_parent(self, parent: rdflib.URIRef):
        self.__parents.append(Uri(parent))
        if not self.__have_ilx_parents:
            self.__have_ilx_parents = parent.startswith(ILX_BASE)

    @property
    def uri(self):
        return self.__uri

    @property
    def label(self):
        return self.__label

    @property
    def parents(self):
        return self.__parents

    @property
    def have_ilx_parents(self):
        return self.__have_ilx_parents

#===============================================================================

ILX_TERM_QUERY = f"""
    prefix ILX: <{ILX_BASE}>
    prefix owl: <http://www.w3.org/2002/07/owl#>
    prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    select ?term ?label ?p1 ?p2 where
    {{
        ?term a owl:Class ;
              rdfs:label ?label ;
              rdfs:subClassOf ?p1 .
        optional {{
            ?p1 a owl:Restriction ;
                owl:onProperty {ILX_PART_OF} ;
                owl:someValuesFrom ?p2 . }}
    }}
    order by ?term"""

class IlxTerms(rdflib.Graph):
#============================
    def __init__(self, ttl_source):
        super().__init__()
        with open(ttl_source) as fp:
            self.parse(fp)

    def term_list(self):
        last_uri = None
        ilx_term = None
        for row in self.query(ILX_TERM_QUERY):
            result_row = cast(rdflib.query.ResultRow, row)
            if result_row.term.startswith(ILX_BASE):
                if ilx_term is None or last_uri != Uri(result_row.term):
                    if ilx_term is not None:
                        yield ilx_term
                    ilx_term = IlxTerm(result_row)
                    last_uri = ilx_term.uri
                if isinstance(result_row.p1, rdflib.URIRef):
                    ilx_term.add_parent(result_row.p1)
                elif (isinstance(result_row.p1, rdflib.BNode)
                  and isinstance(result_row.p2, rdflib.URIRef)):
                    ilx_term.add_parent(result_row.p2)
            if ilx_term is not None:
                yield ilx_term

#===============================================================================

class UberonGraph(nx.DiGraph):
    def __init__(self, json_source):
        super().__init__()
        with open(json_source) as fp:
            data = json.load(fp)
            for node in data['graphs'][0]['nodes']:
                node = Node(node)
                if node.is_uberon:
                    self.add_node(node, label=str(node))
            for edge in data['graphs'][0]['edges']:
                edge = Triple(edge)
                if edge.p == PART_OF or edge.p == IS_A:
                    if edge.s.is_uberon and edge.o.is_uberon:
                        self.add_edge(edge.s, edge.o)

#===============================================================================

class SparcHierarchy:
    def __init__(self, uberon_graph: nx.DiGraph):
        self.__graph = uberon_graph

    def add_ilx_terms(self, ilx_terms: IlxTerms):
    #============================================
        have_ilx_parents = []
        for ilx_term in ilx_terms.term_list():
            if ilx_term.have_ilx_parents:
                have_ilx_parents.append(ilx_term)
            else:
                self.__add_ilx_child(ilx_term)
        depth = 0
        while depth < 3 and len(have_ilx_parents):
            new_parents = []
            for ilx_term in have_ilx_parents:
                # Are all parents now in the graph?
                if functools.reduce(lambda in_graph, p: in_graph and p in self.__graph,
                                    ilx_term.parents, True):
                    self.__add_ilx_child(ilx_term)
                else:
                    new_parents.append(ilx_term)
            have_ilx_parents = new_parents
            depth += 1
        if len(have_ilx_parents):
            raise ValueError('Some Interlex parts are deeply nested')

    def __add_ilx_child(self, ilx: IlxTerm):
    #=======================================
        self.__graph.add_node(ilx.uri, label=ilx.label if ilx.label else ilx.uri)
        furthest_term = None
        max_parent_distance = 0
        for parent in ilx.parents:
            if parent in self.__graph:
                distance = self.distance_to_root(parent)
                if distance > max_parent_distance:
                    furthest_term = parent
                    max_parent_distance = distance
        if furthest_term is not None:
            self.__graph.add_edge(ilx.uri, furthest_term)

    def children(self, term: Uri):
    #=============================
        return list(self.__graph.predecessors(term))

    def distance_to_root(self, source):
    #==================================
        return nx.shortest_path_length(self.__graph, source, ANATOMICAL_ROOT)

    def label(self, term: Uri) -> str:
    #=================================
        return self.__graph.nodes[term]['label']

    def parents(self, term: Uri):
    #============================
        return list(self.__graph.successors(term))

#===============================================================================

