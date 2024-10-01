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
import sqlite3
from typing import Optional

#===============================================================================

from flatmapknowledge import KnowledgeStore

#===============================================================================

PMR_BASE_URL = 'https://models.physiomeproject.org/'

#===============================================================================

PMR_KNOWLEDE_SCHEMA = """
    create table if not exists pmr_models (term text, score number, model text, workspace text, exposure text);
    create index if not exists pmr_models_term_index on pmr_models(term, score);
    create index if not exists pmr_models_exposure_index on pmr_models(exposure);

    create table if not exists pmr_metadata (entity text, metadata text);
    create index if not exists pmr_metadata_term_index on pmr_metadata(entity);

    create virtual table if not exists pmr_text using fts5(entity unindexed, title, description, documentation, tokenize=porter);
"""


#===============================================================================

def clean_text(dictionary: dict[str, Optional[str]], key: str, update=False) -> Optional[str]:
    value = dictionary.pop(key, None)
    if value is not None:
        value = value.strip()
        if value == '':
            value = None
        elif update:
            dictionary[key] = value
    return value

#===============================================================================

def main():
#=========
    parser = argparse.ArgumentParser(description='Update map server knowledge store with PMR knowledge')
    parser.add_argument('--clean', action='store_true', help='Remove all existing index and metadata before updating')
    parser.add_argument('--index', metavar='TERM_TO_PMR', help='JSON file associating anatomical terms with PMR models')
    parser.add_argument('--exposures', metavar='PMR_EXPOSURES', help='JSON file with metadata about PMR exposures')
    parser.add_argument('--knowledge', metavar='KNOWLEDGE_DIR', help="A map server's flatmap root directory containing a knowledge store")
    parser.add_argument('--local', metavar='LOCAL_DATABASE', help="A local database as an alternative to a map server's knowledge store")
    args = parser.parse_args()

    # Check we have a database to update

    if (args.knowledge is     None and args.local is     None
     or args.knowledge is not None and args.local is not None):
        exit('Either a KNOWLEDGE_DIR or LOCAL_DATABASE must be specified, but not both')

    # Check we have input files

    if args.index is None and args.exposures is None:
        exit('At least one of TERM_TO_PMR or PMR_EXPOSURES files must be specified')
    if args.index is not None:
        if not os.path.isfile(args.index) or not os.path.exists(args.index):
            exit(f'Missing TERM_TO_PMR file: {args.index}')
    if args.exposures is not None:
        if not os.path.isfile(args.exposures) or not os.path.exists(args.exposures):
            exit(f'Missing PMR_EXPOSURES file: {args.exposures}')

    # Open our knowledge base

    if args.knowledge is not None:
        if not os.path.isdir(args.knowledge) or not os.path.exists(args.knowledge):
            exit(f'Missing flatmap root directory: {args.knowledge}')
        knowledge_store = KnowledgeStore(args.knowledge, create=False, read_only=False, use_npo=False, use_scicrunch=False)
        db = knowledge_store.db
        if db is None:
            exit('Unable to get knowledge database connection')
    else:
        db = sqlite3.connect(args.local,
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    # Wrap the entire operation in a transaction

    db.executescript(PMR_KNOWLEDE_SCHEMA)
    db.commit()

    if args.index is not None:
        if (args.clean):
            db.execute('delete from pmr_models')
        term_index = json.load(open(args.index))
        for sckan_models in term_index:
            term = sckan_models['sckan_term']
            for model in sckan_models['cellmls']:
                db.execute('insert or replace into pmr_models (term, model, workspace, exposure, score) values (?, ?, ?, ?, ?)',
                                                              (term, model['cellml'], model['workspace'], model.get('exposure'), model['score']))
    if args.exposures is not None:
        if (args.clean):
            db.execute('delete from pmr_metadata')
            db.execute('delete from pmr_text')
        exposure_metadata = json.load(open(args.exposures))
        for metadata in exposure_metadata:
            exposure = metadata.get('exposure')
            if exposure is not None:
                # Clean up title and description fields
                title = clean_text(metadata, 'title', True)
                description = clean_text(metadata, 'description', True)

                # FTS documentation is not in metadata table
                documentation = clean_text(metadata, 'documentation')

                # Update metadata table
                db.execute('insert or replace into pmr_metadata (entity, metadata) values (?, ?)',
                                                                (exposure, json.dumps(metadata)))
                # Update FTS table
                db.execute('insert or replace into pmr_text (entity, title, description, documentation) values (?, ?, ?, ?)',
                                                                (exposure, title, description, documentation))
    # All done, commit transaction and close knowledge store
    db.commit()

    if args.knowledge is not None:
        knowledge_store.close()     # type: ignore

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================

"""

[
    {
        "sckan_term": "UBERON:0010247",
        "label": "choroidal tapetum cellulosum, choroid tapetum cellulosum",
        "cellmls": [
            {
                "cellml": "https://models.physiomeproject.org/workspace/guyton_capillary_dynamics_2008/rawfile/18a2d9f035fb3950ccdae97b7fb21f1bb93d6a67/cap_dynamics_parent.cellml",
                "workspace": "https://models.physiomeproject.org/workspace/guyton_capillary_dynamics_2008",
                "score": 0.7016255855560303,
                "exposure": "https://models.physiomeproject.org/exposure/f3272a51c6e95c70eb1309d30c08d4cf"
            },
            {
                "cellml": "https://models.physiomeproject.org/workspace/guyton_capillary_dynamics_2008/rawfile/18a2d9f035fb3950ccdae97b7fb21f1bb93d6a67/guyton_capillary_dynamics_2008.cellml",
                "workspace": "https://models.physiomeproject.org/workspace/guyton_capillary_dynamics_2008",
                "score": 0.7016255855560303,
                "exposure": "https://models.physiomeproject.org/exposure/f3272a51c6e95c70eb1309d30c08d4cf"
            }
        ]
    },
]

[
    {
        "exposure": "https://models.physiomeproject.org/exposure/7f056cfd284daf3b3bbaf2ae23b0ff5e",
        "title": "Mosekilde, Lading, Yanchuk, Maistrenko, 2001",
        "sha": "aa0e676c403f6edc747b9a481fcfbb039baab391",
        "workspace": "https://models.physiomeproject.org/workspace/mosekilde_lading_yanchuk_maistrenko_2001",
        "omex": "https://models.physiomeproject.org/exposure/7f056cfd284daf3b3bbaf2ae23b0ff5e/download_generated_omex",
        "image": "https://models.physiomeproject.org/workspace/mosekilde_lading_yanchuk_maistrenko_2001/@@rawfile/aa0e676c403f6edc747b9a481fcfbb039baab391/mosekilde_2001.png",
        "authors": "admin",
        "description": ""
    },
]
"""

#===============================================================================
