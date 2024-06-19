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

#===============================================================================

from flatmapknowledge import KnowledgeStore

#===============================================================================

PMR_BASE_URL = 'https://models.physiomeproject.org/'

#===============================================================================

PMR_KNOWLEDE_SCHEMA = """
    create table if not exists pmr_models (term text, score number, model text, workspace text, exposure text);
    create index if not exists pmr_models_term_index on pmr_models(term, score);

    create table if not exists pmr_metadata (entity text, metadata text);
    create index if not exists pmr_metadata_term_index on pmr_metadata(entity);
"""

#===============================================================================

def main():
#=========
    parser = argparse.ArgumentParser(description='Update map server knowledge store with PMR knowledge')
    parser.add_argument('--clean', action='store_true', help='Remove all existing index and metadata before updating')
    parser.add_argument('--index', metavar='TERM_TO_PMR', help='JSON file associating anatomical terms with PMR models')
    parser.add_argument('--exposures', metavar='PMR_EXPOSURES', help='JSON file with metadata about PMR exposures')
    parser.add_argument('knowledge_dir', metavar='KNOWLEDGE_DIR', help="A map server's flatmap root directory containing a knowledge store")
    args = parser.parse_args()

    # Check we have input files

    if args.index is None and args.exposures is None:
        exit(f'At least one of TERM_TO_PMR or PMR_EXPOSURES files must be specified')
    if args.index is not None:
        if not os.path.isfile(args.index) or not os.path.exists(args.index):
            exit(f'Missing TERM_TO_PMR file: {args.index}')
    if args.exposures is not None:
        if not os.path.isfile(args.exposures) or not os.path.exists(args.exposures):
            exit(f'Missing PMR_EXPOSURES file: {args.exposures}')

    # Open our knowledge base

    if not os.path.isdir(args.knowledge_dir) or not os.path.exists(args.knowledge_dir):
        exit(f'Missing flatmap root directory: {args.knowledge_dir}')

    knowledge_store = KnowledgeStore(args.knowledge_dir, create=False, read_only=False, use_npo=False, use_scicrunch=False)
    db = knowledge_store.db
    if db is None:
        exit('Unable to get knowledge database connection')

    # Wrap the entire operation in a transaction

    db.execute('begin')
    db.executescript(PMR_KNOWLEDE_SCHEMA)

    if args.index is not None:
        if (args.clean):
            db.execute('delete from pmr_models')
        term_index = json.load(open(args.index))
        for (term, models) in term_index.items():
            for model in models:
                db.execute('insert or replace into pmr_models (term, model, workspace, exposure, score) values (?, ?, ?, ?, ?)',
                                                              (term, model['cellml'], model['workspace'], model.get('exposure'), model['score']))
    if args.exposures is not None:
        if (args.clean):
            db.execute('delete from pmr_metadata')
        exposure_metadata = json.load(open(args.exposures))
        for metadata in exposure_metadata:
            exposure = metadata.get('exposure')
            if exposure is not None:
                db.execute('insert or replace into pmr_metadata (entity, metadata) values (?, ?)',
                                                                (exposure, json.dumps(metadata)))

    # All done, commit transaction and close knowledge store

    db.commit()
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
}

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
