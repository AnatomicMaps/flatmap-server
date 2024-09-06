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

from tqdm import tqdm

#===============================================================================

import mapknowledge

#===============================================================================

def main(store_directory, knowledge_store, sckan_version, scicrunch_key):
    store = mapknowledge.KnowledgeStore(
        store_directory=store_directory,
        knowledge_base=knowledge_store,
        sckan_version=sckan_version,
        scicrunch_key=scicrunch_key)

    if store.db is None:
        logging.error(f'Unable to open knowledge store {store_directory}/{knowledge_store}')
        exit(1)

    knowledge_source = store.source
    logging.info(f'Loading SCKAN connectivity for source `{knowledge_source}`')

    store.db.execute('begin')
    store.db.execute('delete from knowledge where source=?', (knowledge_source,))
    store.db.execute('delete from connectivity_nodes where source=?', (knowledge_source,))
    store.db.commit()

    paths = store.connectivity_paths()
    progress_bar = tqdm(total=len(paths),
        unit='path', ncols=80,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')

    for path in paths:
        store.entity_knowledge(path, source=knowledge_source)
        progress_bar.update(1)

    store.close()
    progress_bar.close()
    logging.info(f'Loaded connectivity for {len(paths)} paths')

#===============================================================================

DEFAULT_STORE = 'knowledgebase.db'

if __name__ == '__main__':
#=========================

    import argparse

    logging.basicConfig(level=logging.INFO)

    scicrunch_key = os.environ.get('SCICRUNCH_API_KEY')
    if scicrunch_key is None:
        logging.error('Undefined SCICRUNCH_API_KEY -- cannot load SCKAN knowledge')
        exit(1)

    parser = argparse.ArgumentParser(description='Load connectivity knowledge from SCKAN into a local knowledge store.')
    parser.add_argument('--store-directory', required=True, help='Directory containing a knowledge store.')
    parser.add_argument('--knowledge-store', default=DEFAULT_STORE, help=f'Name of knowledge store file. Defaults to `{DEFAULT_STORE}`.')
    parser.add_argument('--sckan-release', help='SCKAN release identifier. Defaults to  latest released version of SCKAN.')
    args = parser.parse_args()

    main(store_directory=args.store_directory,
        knowledge_store=args.knowledge_store,
        sckan_version=args.sckan_release,
        scicrunch_key=scicrunch_key)

#===============================================================================
