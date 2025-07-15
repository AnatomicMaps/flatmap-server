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

import logging
import os

#===============================================================================

from mapserver.competency import CompetencyKnowledge
from mapserver.competency.manager import map_knowledge as get_map_knowledge
from mapserver.settings import settings

#===============================================================================

PG_DATABASE = 'map-knowledge'

DEFAULT_STORE = 'knowledgebase.db'

KNOWLEDGE_USER = os.environ.get('KNOWLEDGE_USER')
KNOWLEDGE_HOST = os.environ.get('KNOWLEDGE_HOST', 'localhost:5432')

#===============================================================================

# Used by `json_map_metadata`

settings['FLATMAP_ROOT'] = os.environ.get('FLATMAP_ROOT', './flatmaps')

#===============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Import Flatmap knowledge into a PostgreSQL knowledge store.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress INFO log messages')
    parser.add_argument('--uuid', required=True, help='Map UUID')

    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO)

    competency_db = CompetencyKnowledge(KNOWLEDGE_USER, KNOWLEDGE_HOST, PG_DATABASE)
    knowledge = get_map_knowledge(args.uuid, competency_db)
    competency_db.import_knowledge(knowledge)

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
