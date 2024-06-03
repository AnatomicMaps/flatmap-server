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
import os
from typing import cast, Iterator

#===============================================================================

import networkx as nx
import rdflib

#===============================================================================

from ..settings import settings

from . import get_metadata
from .rdf_utils import ILX_BASE, Node, Triple, Uri

#===============================================================================

CACHED_MAP_HIERARCHY = 'hierarchy.json'
CACHED_SPARC_HIERARCHY = 'sparc-hierarchy.json'

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
        self.__parents: list[Uri] = []
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
                    self.add_node(node.id, label=str(node))
            for edge in data['graphs'][0]['edges']:
                edge = Triple(edge)
                if edge.p == PART_OF or edge.p == IS_A:
                    if edge.s.is_uberon and edge.o.is_uberon:
                        self.add_edge(edge.s.id, edge.o.id)

#===============================================================================

class SparcHierarchy:
    def __init__(self, uberon_source: str, interlex_source: str):
        hierarchy_file = os.path.join(settings['FLATMAP_ROOT'], CACHED_SPARC_HIERARCHY)
        try:
            with open(hierarchy_file) as fp:
                graph_json = json.load(fp)
                self.__graph = nx.node_link_graph(graph_json, directed=True)
                return
        except Exception:
            pass
        self.__graph = UberonGraph(uberon_source)
        self.__add_ilx_terms(interlex_source)
        graph_json = nx.node_link_data(self.__graph)
        with open(hierarchy_file, 'w') as fp:
            json.dump(graph_json, fp)

    def __add_ilx_terms(self, interlex_source: str):
    #===============================================
        ilx_terms = IlxTerms(interlex_source)
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
            raise ValueError('Some Interlex parts are too deeply nested')

    def __add_ilx_child(self, ilx: IlxTerm):
    #=======================================
        self.__graph.add_node(ilx.uri.id, label=ilx.label if ilx.label else ilx.uri)
        furthest_term = None
        max_parent_distance = 0
        for parent in ilx.parents:
            if parent.id in self.__graph:
                distance = self.distance_to_root(parent)
                if distance > max_parent_distance:
                    furthest_term = parent
                    max_parent_distance = distance
        if furthest_term is not None:
            self.__graph.add_edge(ilx.uri.id, furthest_term.id)

    def distance_to_root(self, source):
    #==================================
        return self.path_length(source, ANATOMICAL_ROOT)

    def has(self, term: Uri) -> bool:
    #=================================
        return term is not None and str(term) in self.__graph

    def label(self, term: Uri) -> str:
    #=================================
        return self.__graph.nodes[term.id]['label']

    def path_length(self, source, target):
    #=====================================
        try:
            return nx.shortest_path_length(self.__graph, source.id, target.id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        return -1

#===============================================================================

class AnatomicalHierarchy:
    def __init__(self):
        self.__sparc_hierarchy = SparcHierarchy(UBERON_ONTOLOGY, NPO_ONTOLOGY)

    def get_hierachy(self, flatmap: str):
        hierarchy_file = os.path.join(settings['FLATMAP_ROOT'], flatmap, CACHED_MAP_HIERARCHY)
        try:
            with open(hierarchy_file) as fp:
                return json.load(fp)
        except Exception:
            pass

        hierarchy_graph = nx.DiGraph()
        hierarchy_graph.add_node(ANATOMICAL_ROOT.id,
            label=self.__sparc_hierarchy.label(ANATOMICAL_ROOT),
            distance=0)

        # Nodes on the graph are SPARC terms, with attributes of the term's label and its distance to
        # a common ``anatomical root``
        map_terms = set(Uri(term) for term in
                        [ann.get('models') for ann in get_metadata(flatmap, 'annotations').values()]
                            if self.__sparc_hierarchy.has(term))
        for term in map_terms:
            distance = self.__sparc_hierarchy.distance_to_root(term)
            if distance > 0:
                hierarchy_graph.add_node(term.id,
                    label=self.__sparc_hierarchy.label(term),
                    distance=distance)

        # Find the shortest path between each pair of SPARC terms used in the flatmap,
        # including to the ANATOMICAL_ROOT node, and if a path exists, add an edge to
        # the graph
        map_terms.add(ANATOMICAL_ROOT)
        for source, target in itertools.permutations(map_terms, 2):
            path_length = self.__sparc_hierarchy.path_length(source, target)
            if path_length > 0:
                hierarchy_graph.add_edge(source.id, target.id, parent_distance=path_length)

        # For each term used by the flatmap find the closest term(s) it is connected to and
        # delete edges connecting to more distant terms
        for term in hierarchy_graph.nodes():
            parent_edges = list(map(lambda edge: {'edge': edge,
                                                  'parent': edge[1],
                                                  'distance': hierarchy_graph.edges[edge]['parent_distance']
                                                 }, hierarchy_graph.out_edges(term)))
            if len(parent_edges):
                parent_edges.sort(key=lambda e: e['distance'])
                distance = parent_edges[0]['distance']
                n = 1
                while n < len(parent_edges) and distance == parent_edges[n]['distance']:
                    n += 1
                while n < len(parent_edges):
                    hierarchy_graph.remove_edge(*parent_edges[n]['edge'])
                    n += 1

        hierarchy = nx.node_link_data(hierarchy_graph)
        with open(hierarchy_file, 'w') as fp:
            json.dump(hierarchy, fp)
        return hierarchy

#===============================================================================
