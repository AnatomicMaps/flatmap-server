#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2019-25  David Brooks
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

from collections import defaultdict
import logging
import os

#===============================================================================

import psycopg as pg

#===============================================================================

from mapknowledge import NERVE_TYPE
from mapknowledge.competency import clean_knowledge_source, CompetencyDatabase
from mapknowledge.competency import KnowledgeList, KnowledgeSource
from mapserver.settings import settings
from mapserver.utils import json_map_metadata

#===============================================================================

PG_DATABASE = 'map-knowledge'

DEFAULT_STORE = 'knowledgebase.db'

KNOWLEDGE_USER = os.environ.get('KNOWLEDGE_USER')
KNOWLEDGE_HOST = os.environ.get('KNOWLEDGE_HOST', 'localhost:5432')

#===============================================================================

# Used by `json_map_metadata`

settings['FLATMAP_ROOT'] = os.environ.get('FLATMAP_ROOT', './flatmaps')

#===============================================================================

def get_map_knowledge(map_uuid: str, competency_db: CompetencyDatabase) -> KnowledgeList:
#========================================================================================
    metadata = json_map_metadata(map_uuid, 'metadata')
    if map_uuid != metadata.get('uuid'):
        raise IOError("Flatmap source UUID doesn't match the provided UUID.")

    sckan_release = metadata.get('connectivity', {}).get('npo', {}).get('release')
    map_knowledge_source = clean_knowledge_source(sckan_release)

    annotations = json_map_metadata(map_uuid, 'annotations')
    annotated_features = { models: feature
                            for feature in annotations.values()
                                if (models := feature.get('models')) is not None }
    descriptions = { row[0]: row[1]
                        for row in competency_db.execute(
                            'select term_id, description from feature_terms where source_id=%s', (map_knowledge_source,)) }
    path_properties = {}
    for row in competency_db.execute(
            'select path_id, alert, biological_sex, disconnected from path_properties where source_id=%s', (map_knowledge_source,)):
        properties = {}
        if row[1] is not None:
            properties['alert'] = row[1]
        if row[2] is not None:
            properties['biologicalSex'] = row[2]
        if row[3] is not None:
            properties['pathDisconnected'] = row[3]
        path_properties[row[0]] = properties

    path_evidence = defaultdict(list)
    for row in competency_db.execute(
            'select term_id, evidence_id from feature_evidence where source_id=%s', (map_knowledge_source,)):
        path_evidence[row[0]].append(row[1])

    path_phenotypes = defaultdict(list)
    for row in competency_db.execute(
            'select path_id, phenotype from path_phenotypes where source_id=%s', (map_knowledge_source,)):
        path_phenotypes[row[0]].append(row[1])

    # Collect all map knowledge
    knowledge_terms = {}

    # Path features (i.e. those with connectivity)
    pathways = json_map_metadata(map_uuid, 'pathways').get('paths', {})
    for path_id, path_knowledge in pathways.items():
        if 'connectivity' not in path_knowledge:
            continue
        annotations = annotated_features.get(path_id, {})
        properties = path_properties.get(path_id, {})
        knowledge_terms[path_id] = {
            'id': path_id,
            'source': map_uuid,
            'label': annotations['label'],
            'long-label': descriptions.get(path_id, annotations['label']),
            'connectivity': path_knowledge['connectivity'],
            'taxons': annotations.get('taxons', []),
            'forward-connections': path_knowledge.get('forward-connections', []),
            'node-phenotypes': path_knowledge.get('node-phenotypes', {}),
            'nerves': path_knowledge.get('node-nerves', []),
            'phenotypes': path_phenotypes.get(path_id, []),
            'references': path_evidence.get(path_id, []),
        }
        if 'alert' in properties:
            knowledge_terms[path_id]['alert'] = properties['alert']
        if 'biologicalSex' in properties:
            knowledge_terms[path_id]['biologicalSex'] = properties['biologicalSex']
        if 'pathDisconnected' in properties:
            knowledge_terms[path_id]['pathDisconnected'] = properties['pathDisconnected']

    # Non-path features with an anatomical term
    for feature_id, properties in annotated_features.items():
        if feature_id not in knowledge_terms:
            knowledge_terms[feature_id] = {
                'id': feature_id,
                'source': map_uuid,
                'label': properties['label'],
                'long-label': descriptions.get(feature_id, properties['label']),
            }
            if properties.get('type') == 'nerve':
                knowledge_terms[feature_id]['type'] = NERVE_TYPE

    return KnowledgeList(KnowledgeSource(map_uuid, sckan_release, metadata['name']), list(knowledge_terms.values()))

#===============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Import Flatmap knowledge into a PostgreSQL knowledge store.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress INFO log messages')
    parser.add_argument('--uuid', required=True, help='Map UUID')

    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO)

    competency_db = CompetencyDatabase(KNOWLEDGE_USER, KNOWLEDGE_HOST, PG_DATABASE)
    knowledge = get_map_knowledge(args.uuid, competency_db)
    competency_db.import_knowledge(knowledge)

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
