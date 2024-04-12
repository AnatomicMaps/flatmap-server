#===============================================================================
#
#  Flatmap viewer and annotation tools
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
from json import JSONDecodeError
from pathlib import Path
import sqlite3

from pprint import pprint

#===============================================================================

import requests

LOOKUP_TIMEOUT = 30    # seconds; for `requests.get()`

#===============================================================================

SCHEMA_UPDATE = '''
begin;
alter table annotations add column itemid text;
drop index annotations_index;
create index annotations_index on annotations(resource, itemid, created, orcid);
drop index features_index;
alter table features rename column item to itemid;
create index features_index on features(resource, itemid, deleted);
commit;
'''

def upgrade_schema(db):
#=====================
    try:
        db.executescript(SCHEMA_UPDATE)
    except sqlite3.OperationalError as error:
        exit(str(error))

#===============================================================================

class ResourceDetails:
    def __init__(self):
        self.__details: dict[str, dict] = {}

    def item_details(self, resource: str, item: str) -> dict:
        if resource not in self.__details:
            annotations = None
            error = None
            if resource.startswith('http'):
                try:
                    response = requests.get(f'{resource}/annotations',
                                            headers={'Accept': 'application/json'},
                                            timeout=LOOKUP_TIMEOUT)
                    if response.status_code == requests.codes.ok:
                        try:
                            annotations = response.json()
                        except JSONDecodeError:
                            error = 'Invalid JSON returned'
                    else:
                        error = response.reason
                except requests.exceptions.RequestException as exception:
                    error = f'Exception: {exception}'
            if error is not None:
                print(f'Cannot get annotations for {resource}: {error}')
            elif annotations is not None:
                self.__details[resource] = annotations
        details = self.__details.get(resource, {})
        item_details = {
            'id': item
        }
        if item in details:
            if 'models' in details[item]:
                item_details['models'] = details[item]['models']
            if 'label' in details[item]:
                item_details['label'] = details[item]['label']
        return item_details

#===============================================================================

def add_item_details(db, details_lookup: ResourceDetails):
#=========================================================
    items = []
    for row in db.execute('select rowid, resource, itemid, item from annotations').fetchall():
        resource = row[1]
        item_id = row[2]
        item = row[3]
        if item_id is None or not item.startswith('{'):
            item_id = item
            item = details_lookup.item_details(resource, item_id)
            items.append({'rowid': row[0], 'item_id': item_id, 'item': json.dumps(item)})
    if len(items):
        pprint(items[:10])
        db.execute('begin')
        db.executemany('update annotations set itemid=:item_id, item=:item where rowid=:rowid', items)
        db.execute('commit')

#===============================================================================

def main():
#==========
    db_path = 'flatmaps/annotation_store.db'
    db_name = Path(db_path).resolve()
    if db_name.exists():
        db = sqlite3.connect(db_name)
        upgrade_schema(db)
        add_item_details(db, ResourceDetails())
    else:
        exit(f'Cannot find `{db_path}`')

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
