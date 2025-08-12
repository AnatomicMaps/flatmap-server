#===============================================================================
#
#  Flatmap server
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

import logging
from typing import Optional

#===============================================================================

import semver

#===============================================================================

from mapknowledge import NERVE_TYPE
from mapknowledge.competency import clean_knowledge_source
from mapknowledge.competency import KnowledgeList, KnowledgeSource

#===============================================================================

from ..settings import settings
from ..utils import json_map_metadata

from .knowledge import CompetencyKnowledge

#===============================================================================

RENDERED_CONNECTIVITY_BASE_VERSION = '1.18.0'

#===============================================================================

ignored_maps: set[str] = set()

def ignore_map(uuid: str, msg: str, log_printer):
#================================================
    if uuid not in ignored_maps:
        ignored_maps.add(uuid)
        log_printer(msg)
    return None

#===============================================================================

def anatomical_map_knowledge(map_uuid: str, competency_db: CompetencyKnowledge) -> Optional[KnowledgeList]:
#==========================================================================================================
    metadata = json_map_metadata(map_uuid, 'metadata')
    if map_uuid != metadata.get('uuid'):
        return ignore_map(map_uuid, f"Flatmap source {map_uuid} doesn't match the provided UUID, ignored.",
                            settings['LOGGER'].error)
    if metadata.get('style', 'anatomical') != 'anatomical':
        return ignore_map(map_uuid, f"{map_uuid} is not an anatomical map, ignored.",
                            settings['LOGGER'].warning)
    creator_version = metadata.get('creator', '').split()[1]
    try:
        invalid_version = (semver.compare(creator_version, RENDERED_CONNECTIVITY_BASE_VERSION) < 0)
    except ValueError:
        invalid_version = True
    if invalid_version:
        return ignore_map(map_uuid, f"{map_uuid} has no rendered connectivity (mapmaker v{creator_version}), ignored.",
                            settings['LOGGER'].warning)

    sckan_release = metadata.get('connectivity', {}).get('npo', {}).get('release', '')
    map_knowledge_source = clean_knowledge_source(sckan_release)

    annotations = json_map_metadata(map_uuid, 'annotations')
    annotated_features = { models: feature
                            for feature in annotations.values()
                                if (models := feature.get('models')) is not None }

    descriptions = competency_db.term_descriptions(map_knowledge_source)
    path_properties = competency_db.path_properties(map_knowledge_source)
    path_evidence = competency_db.path_evidence(map_knowledge_source)
    path_phenotypes = competency_db.path_phenotypes(map_knowledge_source)

    # Collect all map knowledge
    knowledge_terms = {}

    # Path features (i.e. those with connectivity)
    pathways = json_map_metadata(map_uuid, 'pathways').get('paths', {})
    nerve_terms = set()
    for path_id, path_knowledge in pathways.items():
        if 'connectivity' not in path_knowledge or len(path_knowledge['connectivity']) == 0:
            logging.warning(f'{map_uuid}/{path_id} has no connectivity, path not imported.')
            break
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
        nerve_terms.update(term for node in knowledge_terms[path_id]['nerves'] for term in [node[0]] + node[1])

    # Non-path features with an anatomical term
    for feature_id, properties in annotated_features.items():
        if feature_id not in knowledge_terms:
            label = properties.get('label', properties.get('name', feature_id))
            knowledge_terms[feature_id] = {
                'id': feature_id,
                'source': map_uuid,
                'label': label,
                'long-label': descriptions.get(feature_id, label),
            }
            if properties.get('type') == 'nerve' or feature_id in nerve_terms:
                knowledge_terms[feature_id]['type'] = NERVE_TYPE

    map_name = metadata.get('name', metadata.get('describes', metadata['id']))
    return KnowledgeList(KnowledgeSource(map_uuid, sckan_release, map_name), list(knowledge_terms.values()))

#===============================================================================
#===============================================================================
