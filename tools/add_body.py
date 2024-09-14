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

def add_body(db):
#================
    annotations = []
    for row in db.execute('select rowid, annotation from annotations').fetchall():
        annotation = json.loads(row[1])
        if 'body' not in annotation:
            annotation['body'] = {}
            if (comment := annotation.pop('comment', None)) is not None:
                annotation['body']['comment'] = comment
            if (evidence := annotation.pop('evidence', None)) is not None:
                annotation['body']['evidence'] = evidence
            annotations.append({'rowid': row[0], 'annotation': json.dumps(annotation)})
    if len(annotations):
        db.executemany('update annotations set annotation=:annotation where rowid=:rowid', annotations)
        db.commit()

#===============================================================================

def main():
#==========
    db_path = 'flatmaps/annotation_store.db'
    db_name = Path(db_path).resolve()
    if db_name.exists():
        db = sqlite3.connect(db_name)
        add_body(db)
    else:
        exit(f'Cannot find `{db_path}`')

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
