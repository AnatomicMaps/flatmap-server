#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-2023  David Brooks
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

import argparse
import json
import os
from urllib.parse import urljoin

#===============================================================================

from mapserver.knowledgestore import KnowledgeStore

#===============================================================================

PMR_BASE_URL = 'https://models.physiomeproject.org/'

#===============================================================================

def main():
#=========
    parser = argparse.ArgumentParser(description='Update map server knowledge with anatomical term to PMR mapping')
    parser.add_argument('--clean', action='store_true', help='Remove all existing mapping from the knowledge database before updating')
    parser.add_argument('term_file', metavar='TERM_TO_PMR', help='JSON file identifying anatomical terms with PMR models')
    parser.add_argument('knowledge_dir', metavar='KNOWLEDGE_DIR', help="A map server's flatmap root directory")
    args = parser.parse_args()

    if not os.path.isfile(args.term_file) or not os.path.exists(args.term_file):
        exit(f'Missing JSON file: {args.term_file}')

    if not os.path.isdir(args.knowledge_dir) or not os.path.exists(args.knowledge_dir):
        exit(f'Missing flatmap root directory: {args.knowledge_dir}')

    # Open our knowledge base
    knowledge_store = KnowledgeStore(args.knowledge_dir, create=False, read_only=False)
    if knowledge_store.error is not None:
        exit('{}: {}'.format(knowledge_store.error, knowledge_store.db_name))

    with open(args.term_file) as fp:
        term_map = json.loads(fp.read())
    knowledge_store.db.execute('begin')
    if (args.clean):
        knowledge_store.db.execute('delete from pmr_models')
    for (term, models) in term_map.items():
        for model in models:
            knowledge_store.db.execute('insert or replace into pmr_models (term, model, workspace, exposure, score) values (?, ?, ?, ?, ?)',
                                                        (term, model['cellml'], model['workspace'], model.get('exposure'), model['score']))
    knowledge_store.db.commit()
    knowledge_store.close()

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================

"""
{
    "UBERON:0001226": [
        {
            "cellml": "https://models.physiomeproject.org/workspace/thomas_2000/rawfile/6e123e79c616535a3abc555552f96b87e4fee556/thomas_2000.cellml",
            "workspace": "https://models.physiomeproject.org/workspace/thomas_2000",
            "exposure": "https://models.physiomeproject.org/exposure/16c44069cf597b2fe1a3cbc0acc03172",
            "score": 0.9161473512649536
        },
        {
            "cellml": "https://models.physiomeproject.org/workspace/584/rawfile/ade7933153a72bb89e0b02d75db92d6e4be285f5/thomas_2000.cellml",
            "workspace": "https://models.physiomeproject.org/workspace/584",
            "score": 0.9161473512649536
        }
    ],
"""

#===============================================================================
