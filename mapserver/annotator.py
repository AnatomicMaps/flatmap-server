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

import flask            # type: ignore

from .server import annotator_blueprint, settings, logged_in_user

#===============================================================================

ANNOTATION_SCHEMA = """
    begin;
    create table annotations (map text, feature text, created text, creator text, property text, value text);
    create index annotations_index on annotations(map, feature, created, creator, property);
    commit;
"""

PROVENANCE_PROPERTIES = [
    'rdfs:comment',
    'prov:wasDerivedFrom',
]

#===============================================================================

class AnnotatorDatabase:
    def __init__(self, db_path):
        # Create knowledge base if it doesn't exist and we are allowed to
        db_name = Path(db_path).resolve()
        if not db_name.exists():
            db = sqlite3.connect(db_name)
            db.executescript(ANNOTATION_SCHEMA)
            db.close()
        self.__db = sqlite3.connect(db_name)

    def close(self):
    #===============
        if self.__db is not None:
            self.__db.close()
            self.__db = None

    def annotated_features(self, map_id: str):
    #=========================================
        result = []
        if self.__db is not None:
            result = [row[0]
                        for row in self.__db.execute('''select distinct feature
                                                        from annotations where map=?
                                                         order by feature''',
                                                    (map_id, )).fetchall()]
        return result

    def get_annotations(self, map_id: str, feature_id: str) -> list[dict]:
    #=====================================================================
        def provenance_dict(creation, properties):
            prov_record = properties.copy()
            prov_record.update({
                'rdf:type': 'prov:Entity',
                'dct:subject': f'flatmaps:{map_id}/{feature_id}',
                'dct:created': creation[0],
                'dct:creator': json.loads(creation[1])
            })
            return prov_record

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
                    result.append(provenance_dict(creation, properties))
                    creation = (row[0], row[1])
                    properties = {}
                properties[row[2]] = json.loads(row[3])
            if len(properties) and creation is not None:
                result.append(provenance_dict(creation, properties))
        return result

    def update_annotation(self, map_id: str, feature_id: str, annotation: dict):
    #===========================================================================
        if self.__db is not None and annotation.get('rdf:type') == 'prov:Entity':
            self.__db.execute('begin')
            created = datetime.now(tz=timezone.utc).isoformat(timespec='seconds')
            creator = annotation.get('dct:creator', '')
            self.__db.executemany('''insert into annotations
                                        (map, feature, created, creator, property, value)
                                        values (?, ?, ?, ?, ?, ?)''',
                [(map_id, feature_id, created, json.dumps(creator), property, json.dumps(value))
                    for (property, value) in [(property, annotation.get(property))
                                                for property in PROVENANCE_PROPERTIES]
                                          if value is not None
                ])
            self.__db.commit()

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

@annotator_blueprint.route('<string:map_id>/', methods=['GET'])
def annotated_features(map_id):
    annotator_db = AnnotatorDatabase(os.path.join(settings['FLATMAP_ROOT'], 'annotation.db'))
    if flask.request.method == 'GET':
        features = annotator_db.annotated_features(map_id)
        annotator_db.close()
        return flask.jsonify(features)

#===============================================================================

@annotator_blueprint.route('<string:map_id>/<path:feature_id>', methods=['GET', 'POST'])
def annotate_feature(map_id, feature_id):
    annotator_db = AnnotatorDatabase(os.path.join(settings['FLATMAP_ROOT'], 'annotation.db'))
    if flask.request.method == 'GET':
        annotations = annotator_db.get_annotations(map_id, feature_id)
        annotator_db.close()
        return flask.jsonify(annotations)
    elif flask.request.method == 'POST':
        annotation = flask.request.get_json()
        if annotation.get('dct:creator', '') != logged_in_user():
            return flask.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})
        else:
            annotator_db.update_annotation(map_id, feature_id, annotation)
            annotator_db.close()
            audit(remote_addr(flask.request), annotation)
            return flask.jsonify({'success': 'Annotation updated'})

#===============================================================================
