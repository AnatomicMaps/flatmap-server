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
from pathlib import Path
import sqlite3

#===============================================================================

ORCID_SCHEMA_UPDATE = '''
alter table annotations add column orcid text;
drop index annotations_index;
create index annotations_index on annotations(resource, item, created, orcid);
'''

#===============================================================================

def set_orcids(db):
#==================
    try:
        db.executescript(ORCID_SCHEMA_UPDATE)
        db.commit()
    except sqlite3.OperationalError as error:
        exit(str(error))

    orcids = []
    for row in db.execute('select rowid, creator from annotations').fetchall():
        creator = json.loads(row[1])
        if (orcid := creator.get('orcid')) is not None:
            orcids.append({'rowid': row[0], 'orcid': orcid})
    if len(orcids):
        db.executemany('update annotations set orcid=:orcid where rowid=:rowid', orcids)
        db.commit()

#===============================================================================

def main():
#==========
    db_path = 'flatmaps/annotation_store.db'
    db_name = Path(db_path).resolve()
    if db_name.exists():
        db = sqlite3.connect(db_name)
        set_orcids(db)
    else:
        exit(f'Cannot find `{db_path}`')

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
