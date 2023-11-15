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
from functools import wraps
from pathlib import Path
import json
import os
import sqlite3
import uuid

import flask            # type: ignore

from .server import annotator_blueprint, settings
from .pennsieve import get_user

#===============================================================================
#===============================================================================

ANNOTATION_STORE_SCHEMA = """
    begin;
    create table annotations (annotation text, resource text, item text, created text, creator text, property text, value text);
    create index annotation_index on annotations(annotation);
    create index annotations_index on annotations(resource, item, created, creator, property);
    commit;
"""

PROVENANCE_PROPERTIES = [
    'rdfs:comment',
    'prov:wasDerivedFrom',
]

#===============================================================================

class AnnotationStore:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(settings['FLATMAP_ROOT'], 'annotation_store.db')
        # Create annotation store if it doesn't exist
        db_name = Path(db_path).resolve()
        if not db_name.exists():
            db = sqlite3.connect(db_name)
            db.executescript(ANNOTATION_STORE_SCHEMA)
            db.close()
        self.__db = sqlite3.connect(db_name)

    def close(self):
    #===============
        if self.__db is not None:
            self.__db.close()
            self.__db = None

    def annotated_items(self, resource_id: str) -> list[str]:
    #========================================================
        result = []
        if self.__db is not None:
            result = [row[0]
                        for row in self.__db.execute('''select distinct item
                                                        from annotations where resource=?
                                                         order by item''',
                                                    (resource_id, )).fetchall()]
        return result

    def annotations(self, resource_id: str, item_id: str) -> list[dict]:
    #===================================================================
        def provenance_dict(id_creation, properties):
            prov_record = properties.copy()
            prov_record.update({
                'rdf:type': 'prov:Entity',
                'dct:subject': f'flatmaps:{resource_id}/{item_id}',
                'dct:created': id_creation[1],
                'dct:creator': json.loads(id_creation[2])
            })
            return prov_record

        result = []
        if self.__db is not None:
            id_creation = None
            properties = {}
            for row in self.__db.execute('''select id, created, creator, property, value
                                            from annotations where resource=? and item=?
                                            order by id, created desc, creator''',
                                        (resource_id, item_id)).fetchall():
                if id_creation is None:
                    id_creation = (row[0], row[1], row[2])
                elif id_creation != (row[0], row[1], row[2]):
                    result.append(provenance_dict(id_creation, properties))
                    id_creation = (row[0], row[1], row[2])
                    properties = {}
                properties[row[3]] = json.loads(row[4])
            if len(properties) and id_creation is not None:
                result.append(provenance_dict(id_creation, properties))
        return result

    def annotation(self, annotation_id) -> dict:
    #===========================================
        result = []
        if self.__db is not None:
            creation = None
            properties = {}
            for row in self.__db.execute('''select created, creator, property, value
                                            from annotations where id=?
                                            order by created desc, creator''',
                                        (annotation_id, )).fetchall():
                if creation is None:
                    creation = (row[0], row[1])
                elif creation != (row[0], row[1]):
                    result.append(provenance_dict(creation, properties))
                    id_creation = (row[0], row[1])
                    properties = {}
                properties[row[2]] = json.loads(row[3])
            if len(properties) and creation is not None:
                result.append(provenance_dict(creation, properties))
        return result

    def add_annotation(self, annotation: dict) -> dict:
    #==================================================
        error = ''
        if self.__db is not None:
            created = annotation.get('created')
            if created is None:
                created = datetime.now(tz=timezone.utc).isoformat(timespec='seconds')
            creator = annotation.get('creator')
            resource_id = annotation.get('resource')
            item_id = annotation.get('item')

            if resource_id and item_id and creator:
##            if self.__db is not None and annotation.get('rdf:type') == 'prov:Entity':
                self.__db.execute('begin')
                try:
                    self.__db.executemany('''insert into annotations
                                                (map, feature, created, creator, property, value)
                                                values (?, ?, ?, ?, ?, ?)''',
                        [(resource_id, item_id, created, json.dumps(creator), property, json.dumps(value))
                            for (property, value) in [(property, annotation.get(property))
                                                        for property in PROVENANCE_PROPERTIES]
                                                  if value is not None
                        ])
                    self.__db.commit()
                except sqlite3.OperationalError as err:
                    self.__db.rollback()
                    error = str(err)
        else:
            error = 'No annotation database...'
        return {'error': error}

#===============================================================================

def authenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if flask.request.method == 'GET':
            parameters = flask.request.args
        elif flask.request.method == 'POST':
            parameters = flask.request.get_json()
        else:
            parameters = {}
        session_key = parameters.get('session', '')
        if session_key[:-1] == str(uuid.uuid5(uuid.NAMESPACE_URL, parameters.get('key', ''))):
            flask.g.update = session_key[-1] == 'Y'
            return f(*args, **kwargs)
        response = flask.make_response('{"error": "forbidden"}', 403)
        return response
    return decorated_function

#===============================================================================

@annotator_blueprint.route('authenticate', methods=['GET'])
def authenticate():
    parameters = flask.request.args
    if (key := parameters.get('key')) is not None:
        user_data = get_user(key)
    else:
        user_data = {'error': 'forbidden'}
    if 'error' not in user_data:
        session_key = (str(uuid.uuid5(uuid.NAMESPACE_URL, key))
                    + ('Y' if user_data.get('canUpdate', False) else 'N'))
        response = flask.make_response(json.dumps({
            'session': session_key,
            'data': user_data
        }))
    else:
        response = flask.make_response(json.dumps(user_data), 403)
    response.mimetype = 'application/json'
    return response

#===============================================================================

@annotator_blueprint.route('unauthenticate/', methods=['GET'])
def unauthenticate():
    response = flask.make_response('{"success": "Unauthenticated"}')
    response.mimetype = 'application/json'
    return response

#===============================================================================

@annotator_blueprint.route('items/<string:resource_id>', methods=['GET'])
@authenticated
def annotated_items(resource_id: str):
    annotation_store = AnnotationStore()
    items = annotation_store.annotated_items(resource_id)
    annotation_store.close()
    return flask.jsonify(items)

#===============================================================================

@annotator_blueprint.route('annotations/<string:resource_id>/<string:item_id>', methods=['GET'])
@authenticated
def annotations(resource_id: str, item_id: str):
    annotation_store = AnnotationStore()
    items = annotation_store.annotations(resource_id, item_id)
    annotation_store.close()
    return flask.jsonify(items)

#===============================================================================

@annotator_blueprint.route('annotation/<string:annotation_id>', methods=['GET'])
@authenticated
def annotation(annotation_id: str, item_id: str):
    annotation_store = AnnotationStore()
    annotation = annotation_store.annotation(annotation_id)
    annotation_store.close()
    return flask.jsonify(annotation)

#===============================================================================

@annotator_blueprint.route('annotation/', methods=['POST'])
@authenticated
def add_annotation():
    annotation_store = AnnotationStore()
    if flask.request.method == 'POST' and flask.g.update:
        annotation = flask.request.get_json().get('data', {})
        result = annotation_store.add_annotation(annotation)
    else:
        result = '{"error": "forbidden"}', 403, {'mimetype': 'application/json'}
    annotation_store.close()
    return flask.jsonify(result)

#===============================================================================
#===============================================================================
