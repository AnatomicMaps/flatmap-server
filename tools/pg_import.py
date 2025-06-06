#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2019-21  David Brooks
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
import logging
import os
from typing import Any, Optional
from tqdm import tqdm
import pathlib

#===============================================================================

import psycopg as pg
from landez.sources import MBTilesReader

#===============================================================================

from mapknowledge import KnowledgeStore, NERVE_TYPE

#===============================================================================

PG_DATABASE = 'map-knowledge'

DEFAULT_STORE = 'knowledgebase.db'

KNOWLEDGE_USER = os.environ.get('KNOWLEDGE_USER')
KNOWLEDGE_HOST = os.environ.get('KNOWLEDGE_HOST', 'localhost:5432')
FLATMAP_ROOT = os.environ.get('FLATMAP_ROOT')

#===============================================================================

def clean_source(source: str) -> str:
    if source.endswith('-npo'):
        return source[:-4]
    return source

#===============================================================================

type KnowledgeDict = dict[str, Any]

class KnowledgeList:
    def __init__(self, source: str, knowledge: Optional[list[KnowledgeDict]]=None):
        self.__source = clean_source(source)
        if knowledge is None:
            self.__knowledge: list[KnowledgeDict] = []
        else:
            self.__knowledge = knowledge

    @property
    def source(self):
        return self.__source

    @property
    def knowledge(self):
        return self.__knowledge

    def append(self, knowledge: KnowledgeDict):
        self.__knowledge.append(knowledge)

#===============================================================================

NODE_PHENOTYPES = [
    'ilxtr:hasSomaLocatedIn',
    'ilxtr:hasAxonPresynapticElementIn',
    'ilxtr:hasAxonSensorySubcellularElementIn',
    'ilxtr:hasAxonLeadingToSensorySubcellularElementIn',
    'ilxtr:hasAxonLocatedIn',
    'ilxtr:hasDendriteLocatedIn',
]
NODE_TYPES = [
    NERVE_TYPE,
]

def setup_anatomical_types(cursor):
#==================================
    cursor.execute('DELETE FROM anatomical_types at WHERE NOT EXISTS (SELECT 1 FROM path_node_types pt WHERE at.type_id = pt.type_id)')
    cursor.executemany('INSERT INTO anatomical_types (type_id, label) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                       [(type, type) for type in NODE_PHENOTYPES + NODE_TYPES])

#===============================================================================

def delete_source_from_tables(cursor, source: str):
#==================================================
    cursor.execute('DELETE FROM path_taxons WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM feature_evidence WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_edges WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_features WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_node_features WHERE source_id=%s', (source,  ))
    cursor.execute('DELETE FROM path_forward_connections WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_node_types WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_phenotypes WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_properties WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM path_nodes WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM feature_types WHERE source_id=%s', (source, ))
    cursor.execute('DELETE FROM feature_terms WHERE source_id=%s', (source, ))

def update_connectivity(cursor, knowledge: KnowledgeList):
#=========================================================
    source = knowledge.source
    progress_bar = tqdm(total=len(knowledge.knowledge),
        unit='records', ncols=80,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
    for record in knowledge.knowledge:
        if source == clean_source(record.get('source', '')):
            if (connectivity := record.get('connectivity')) is not None:
                path_id = record['id']

                # Taxons
                taxons = record.get('taxons', ['NCBITaxon:40674'])
                cursor.executemany('INSERT INTO taxons (taxon_id) VALUES (%s) ON CONFLICT DO NOTHING',
                                   ((taxon,) for taxon in taxons))

                # Path taxons
                with cursor.copy("COPY path_taxons (source_id, path_id, taxon_id) FROM STDIN") as copy:
                    for taxon in taxons:
                        copy.write_row((source, path_id, taxon))

                # Evidence
                evidence = record.get('references', [])
                cursor.executemany('INSERT INTO evidence (evidence_id) VALUES (%s) ON CONFLICT DO NOTHING',
                                   ((evidence,) for evidence in evidence))

                # Path evidence
                with cursor.copy("COPY feature_evidence (source_id, term_id, evidence_id) FROM STDIN") as copy:
                    for evidence_id in evidence:
                        copy.write_row((source, path_id, evidence_id))

                # Nodes
                nodes = set(json.dumps(node) for (node, _) in connectivity) | set(json.dumps(node) for (_, node) in connectivity)
                cursor.executemany('INSERT INTO path_nodes (source_id, path_id, node_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                                   ((source, path_id, node,) for node in nodes))

                # Node features
                node_features = [ (source, path_id, node, feature)
                                        for (node, features) in [(node, json.loads(node)) for node in nodes]
                                            for feature in [features[0]] + features[1] ]
                cursor.executemany('INSERT INTO path_node_features (source_id, path_id, node_id, feature_id) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING',
                                    node_features)

                # Path edges
                path_nodes = [ (source, path_id, json.dumps(node_0), json.dumps(node_1)) for (node_0, node_1) in connectivity ]
                with cursor.copy("COPY path_edges (source_id, path_id, node_0, node_1) FROM STDIN") as copy:
                    for row in path_nodes:
                        copy.write_row(row)

                # Path features
                path_features = [(source, path_id, feature) for feature in set([nf[3] for nf in node_features])]
                with cursor.copy("COPY path_features (source_id, path_id, feature_id) FROM STDIN") as copy:
                    for row in path_features:
                        copy.write_row(row)

                # Forward connections
                forward_connections = [(source, path_id, forward_path) for forward_path in record.get('forward-connections', [])]
                with cursor.copy("COPY path_forward_connections (source_id, path_id, forward_path_id) FROM STDIN") as copy:
                    for row in forward_connections:
                        copy.write_row(row)

                # Path node types
                node_types = []
                node_phenotypes = record.get('node-phenotypes', {})
                for type, nodes in node_phenotypes.items():
                    node_types.extend([(source, path_id, json.dumps(node), type)
                                            for node in nodes])
                node_types.extend([(source, path_id, json.dumps(node), NERVE_TYPE)
                                        for node in record.get('nerves', [])])
                with cursor.copy("COPY path_node_types (source_id, path_id, node_id, type_id) FROM STDIN") as copy:
                    for row in node_types:
                        copy.write_row(row)

                # Path phenotypes
                with cursor.copy("COPY path_phenotypes (source_id, path_id, phenotype) FROM STDIN") as copy:
                    for phenotype in record.get('phenotypes', []):
                        copy.write_row((source, path_id, phenotype))

                # General path properties
                cursor.execute('INSERT INTO path_properties (source_id, path_id, biological_sex, alert, disconnected) VALUES (%s, %s, %s, %s, %s)',
                                   (source, path_id, record.get('biologicalSex'), record.get('alert'), record.get('pathDisconnected')))

        progress_bar.update(1)
    progress_bar.close()

def update_features(cursor, knowledge: KnowledgeList):
#=====================================================
    source = knowledge.source
    cursor.execute('DELETE FROM feature_terms WHERE source_id=%s', (source, ))

    for record in knowledge.knowledge:
        if source == clean_source(record.get('source', '')):

            # Feature terms
            with cursor.copy("COPY feature_terms (source_id, term_id, label, description) FROM STDIN") as copy:
                copy.write_row([source, record['id'], record.get('label'), record.get('long-label')])

            # Feature types
            with cursor.copy("COPY feature_types (source_id, term_id, type_id) FROM STDIN") as copy:
                if (term_type:=record.get('type')) is not None:
                    copy.write_row([source, record['id'], term_type])

def update_knowledge_source(cursor, source):
#===========================================
    cursor.execute('INSERT INTO knowledge_sources (source_id) VALUES (%s) ON CONFLICT DO NOTHING', (source,))

#===============================================================================

def pg_import(uuid):
#=======================================
    knowledge = map_knowledge(uuid)
    user = f'{KNOWLEDGE_USER}@' if KNOWLEDGE_USER else ''
    with pg.connect(f'postgresql://{user}{KNOWLEDGE_HOST}/{PG_DATABASE}') as db:
        with db.cursor() as cursor:
            delete_source_from_tables(cursor, knowledge.source)
            setup_anatomical_types(cursor)
            update_knowledge_source(cursor, knowledge.source)
            update_features(cursor, knowledge)
            update_connectivity(cursor, knowledge)
        db.commit()

#===============================================================================

def map_knowledge(uuid) -> KnowledgeList:
#========================================
    mbtiles = pathlib.Path(FLATMAP_ROOT) / uuid / 'index.mbtiles'
    if not mbtiles.exists():
        raise FileNotFoundError(f"MBTiles file not found at: {mbtiles}")

    store = KnowledgeStore(
        store_directory = FLATMAP_ROOT,
        knowledge_base = DEFAULT_STORE,
        read_only = False,
        use_sckan = False
    )

    reader = MBTilesReader(mbtiles)

    # Load metadata
    row = reader._query("SELECT value FROM metadata WHERE name='metadata'").fetchone()
    metadata = json.loads(row[0])
    if uuid != metadata.get('uuid'):
        raise IOError("Flatmap source UUID doesn't match the provided UUID.")

    sckan_release = metadata.get('connectivity', {}).get('npo', {}).get('release')

    # Load pathways
    row = reader._query("SELECT value FROM metadata WHERE name='pathways'").fetchone()
    pathways = json.loads(row[0]).get('paths', {})
    knowledge_terms = {}

    for path_id, path in pathways.items():
        if 'connectivity' not in path:
            continue

        db_knowledge = store.entity_knowledge(path_id, sckan_release)
        knowledge_terms[path_id] = {
            'id': path_id,
            'label': db_knowledge['label'],
            'long-label': db_knowledge['long-label'],
            'connectivity': path['connectivity'],
            'taxons': [metadata.get('taxon', '')],
            'forward-connections': path['forward-connections'],
            'node-phenotypes': path['node-phenotypes'],
            'nerves': path.get('node-nerves', []),
            'pathDisconnected': db_knowledge['pathDisconnected'],
            'phenotypes': db_knowledge.get('phenotypes', []),
            'source': uuid,
            'references': db_knowledge.get('references', []),
            'alert': db_knowledge.get('alert', [])
        }

    # Load annotations
    row = reader._query("SELECT value FROM metadata WHERE name='annotations'").fetchone()
    annotations = json.loads(row[0])

    for feature in annotations.values():
        model = feature.get('models')
        if model and model not in knowledge_terms:
            db_knowledge = store.entity_knowledge(model, sckan_release)
            knowledge_terms[model] = {
                'id': model,
                'label': db_knowledge['label'],
                'source': uuid,
                **({'type': db_knowledge['type']} if 'type' in db_knowledge else {})
            }

    return KnowledgeList(uuid, list(knowledge_terms.values()))

#===============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Import Flatmap knowledge into a PostgreSQL knowledge store.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress INFO log messages')
    parser.add_argument('--uuid', required=True, help='Map UUID')

    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO)
    pg_import(args.uuid)

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
