#===============================================================================
#
#  Flatmap viewer and annotation tools
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

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3

import flask

from .server import flatmap_blueprint, get_metadata, settings

#===============================================================================

ANNOTATION_SCHEMA = """
    begin;
    create table annotations (map text, feature text, created text, creator text, property text, value text);
    create index annotations_index on annotations(map, feature, created, creator, property);
    commit;
"""

#===============================================================================

class AnnotationDatabase:
    def __init__(self, db_path):
        # Create knowledge base if it doesn't exist and we are allowed to
        db_name = Path(db_path).resolve()
        if not db_name.exists():
            db = sqlite3.connect(db_name)
            db.executescript(ANNOTATION_SCHEMA)
            db.close()
        self.__db = sqlite3.connect(db_name)

    def close(self):
        if self.__db is not None:
            self.__db.close()
            self.__db = None

    def get_annotations(self, map_id: str, feature_id: str) -> list[dict]:
        result = []
        if self.__db is not None:
            creation = None
            properties = {}
            for row in self.__db.execute('''select created, creator, property, value
                                            from annotations where map=? and feature=?
                                            order by created desc, creator''',
                                        (map_id, feature_id)).fetchall():
                if creation is None:
                    creation = (row[0], row[1])
                elif creation != (row[0], row[1]):
                    result.append({
                        'created': creation[0],
                        'creator': json.loads(creation[1]),
                        'properties': properties
                    })
                    creation = (row[0], row[1])
                    properties = {}
                properties[row[2]] = json.loads(row[3])
            if len(properties) and creation is not None:
                result.append({
                    'created': creation[0],
                    'creator': json.loads(creation[1]),
                    'properties': properties
                })
        return result

    def post_annotations(self, map_id: str, feature_id: str, annotations: dict):
        if self.__db is not None:
            self.__db.execute('begin')
            created = datetime.now(tz=timezone.utc).isoformat(timespec='seconds')
            creator = annotations.get('creator', '')
            self.__db.executemany('''insert into annotations
                                        (map, feature, created, creator, property, value)
                                        values (?, ?, ?, ?, ?, ?)''',
                [(map_id, feature_id, created, json.dumps(creator), property, json.dumps(value))
                    for property, value in annotations.get('properties', {}).items()])
            self.__db.commit()

#===============================================================================

#===============================================================================

def remote_addr(req):
#====================
    if req.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return req.environ['REMOTE_ADDR']
    else:
        return req.environ['HTTP_X_FORWARDED_FOR']

def audit(user_ip, new_value):
#=============================
    with open(os.path.join(settings['FLATMAP_ROOT'], 'audit.log'), 'a') as aud:
        aud.write('{}\n'.format(json.dumps({
            'time': datetime.now(tz=timezone.utc).isoformat(timespec='seconds'),
            'ip': user_ip,
            'new': json.dumps(new_value)
        })))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/annotations')
def map_annotations(map_id):
    return flask.jsonify(get_metadata(map_id, 'annotations'))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/annotations/<path:feature_id>', methods=['GET', 'POST'])
def feature_annotations(map_id, feature_id):
    annotation_db = AnnotationDatabase(os.path.join(settings['FLATMAP_ROOT'], 'annotation.db'))
    if flask.request.method == 'GET':
        annotations = annotation_db.get_annotations(map_id, feature_id)
        annotation_db.close()
        return flask.jsonify(annotations)
    elif flask.request.method == 'POST':
        annotations = json.loads(flask.request.get_json())
        annotation_db.post_annotations(map_id, feature_id, annotations)
        annotation_db.close()
        audit(remote_addr(flask.request), annotations)
        return 'Annotations posted'

