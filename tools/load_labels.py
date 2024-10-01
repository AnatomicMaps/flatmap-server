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

import json
from pathlib import Path
import sqlite3
from typing import cast, Optional

#===============================================================================

import networkx as nx
import rdflib

#===============================================================================

from mapserver.knowledge.rdf_utils import ILX_BASE, UBERON_BASE, Uri

#===============================================================================

NPO_ONTOLOGY = './ontologies/npo.ttl'
UBERON_ONTOLOGY = './ontologies/uberon-basic.json'

#===============================================================================

class Term:
    def __init__(self, entity: str, label: Optional[str] = None):
        self.__uri = Uri(entity)
        self.__label = label if label else entity

    @classmethod
    def term_from_query(cls, result_row: rdflib.query.ResultRow):
        return cls(result_row.term, result_row.get('label'))

    @property
    def uri(self):
        return self.__uri.id

    @property
    def label(self):
        return self.__label

#===============================================================================

ILX_TERM_QUERY = f"""
    prefix ILX: <{ILX_BASE}>
    prefix owl: <http://www.w3.org/2002/07/owl#>
    prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    select ?term ?label where
    {{
        ?term a owl:Class ;
              rdfs:label ?label .
    }}
    order by ?term"""

#===============================================================================

class IlxTerms(rdflib.Graph):
    def __init__(self, ttl_source):
        super().__init__()
        with open(ttl_source) as fp:
            self.parse(fp)

    def term_list(self):
        for row in self.query(ILX_TERM_QUERY):
            result_row = cast(rdflib.query.ResultRow, row)
            if result_row.term.startswith(ILX_BASE):
                yield Term.term_from_query(result_row)

#===============================================================================

class UberonTerms:
    def __init__(self, json_source):
        super().__init__()
        with open(json_source) as fp:
            self.__data = json.load(fp)

    def term_list(self):
        for node in self.__data['graphs'][0]['nodes']:
            if node['id'].startswith(UBERON_BASE):
                yield Term(node['id'], node.get('lbl'))

#===============================================================================

def update_labels(db):
    uberon_terms = UberonTerms(UBERON_ONTOLOGY)
    ilx_terms = IlxTerms(NPO_ONTOLOGY)

    db.execute('delete from labels where entity like "UBERON:%"')
    db.executemany('insert into labels (entity, label) values (?, ?)',
        [(t.uri, t.label) for t in uberon_terms.term_list()])
    db.execute('delete from labels where entity like "ILX:%"')
    db.executemany('insert into labels (entity, label) values (?, ?)',
        [(t.uri, t.label) for t in ilx_terms.term_list()])
    db.commit()

#===============================================================================

def main():
    db_path = 'flatmaps/knowledgebase.db'
    db_name = Path(db_path).resolve()
    if db_name.exists():
        db = sqlite3.connect(db_name)
        update_labels(db)
    else:
        exit(f'Cannot find `{db_path}`')

#===============================================================================
