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
from typing import Optional
import uuid

import flask            # type: ignore

from .server import annotator_blueprint, settings
from .pennsieve import get_user

#===============================================================================
'''
/**
 * Annotation about an item in a resource.
 */
export interface UserAnnotation
{
    resource: string
    item: string
    evidence: URL[]
    comment: string
}

interface AnnotationRequest extends UserAnnotation
{
    created: string    // timestamp...
    creator: UserData
}

/**
 * Full annotation about an item in a resource.
 */
export interface Annotation extends AnnotationRequest
{
    id: URL
}
'''
#===============================================================================

ANNOTATION_STORE_SCHEMA = """
    begin;
    create table annotations (resource text, item text, created text, creator text, annotation text);
    create index annotations_index on annotations(resource, item, created, creator);
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
        items = []
        if self.__db is not None:
            items = [row[0]
                        for row in self.__db.execute('''select distinct item
                                                        from annotations where resource=?
                                                         order by item''',
                                                    (resource_id, )).fetchall()]
        return items

    def annotations(self, resource_id: str, item_id: str) -> list[dict]:
    #===================================================================
        result = []
        if self.__db is not None:
            for row in self.__db.execute('''select created, creator, annotation
                                        from annotations where resource=? and item=?
                                        order by created desc, creator''',
                                    (resource_id, item_id)).fetchall():
                annotation = {
                    'resource': resource_id,
                    'item': item_id,
                    'created': row[0],
                    'creator': json.loads(row[1])
                }
                annotation.update(json.loads(row[2]))
                result.append(annotation)
        return result

    def annotation(self, annotation_id) -> dict:
    #===========================================
        annotation = {}
        if self.__db is not None:
            row = self.__db.execute('''select resource, item, created, creator, annotation
                                        from annotations where rowid=?''',
                                        (annotation_id, )).fetchone()
            if row is not None:
                annotation = {
                    'resource': row[0],
                    'item': row[1],
                    'created': row[2],
                    'creator': json.loads(row[3])
                }
                annotation.update(json.loads(row[4]))
        return annotation

    def add_annotation(self, annotation: dict) -> dict:
    #==================================================
        result = {}
        if self.__db is not None:
            created = annotation.pop('created', None)
            if created is None:
                created = datetime.now(tz=timezone.utc).isoformat(timespec='seconds')
            creator = annotation.pop('creator', None)
            resource_id = annotation.pop('resource', None)
            item_id = annotation.pop('item', None)
            if resource_id and item_id and creator:
                creator.pop('canUpdate', None)
                try:
                    cursor = self.__db.cursor()
                    cursor.execute('''insert into annotations
                        (resource, item, created, creator, annotation) values (?, ?, ?, ?, ?)''',
                        (resource_id, item_id, created, json.dumps(creator), json.dumps(annotation)))
                    cursor.execute('commit')
                    result['annotationId'] = cursor.lastrowid
                except sqlite3.OperationalError as err:
                    result['error'] = str(err)
        else:
            result['error'] = 'No annotation database...'
        return result

#===============================================================================

__sessions: dict[str, dict] = {}

def __session_key(key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))

def __new_session(key: str, data: dict) -> str:
    session_key = __session_key(key)
    __sessions[session_key] = data
    return session_key

def __session_data(session_key: str) -> Optional[dict]:
    return __sessions.get(session_key)

def __del_session(session_key: str) -> bool:
    return __sessions.pop(session_key, None) is not None

#===============================================================================

def __authenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if flask.request.method == 'GET':
            parameters = flask.request.args
        elif flask.request.method == 'POST':
            parameters = flask.request.get_json()
        else:
            parameters = {}
        if ((key := parameters.get('key')) is not None
          and (session_key := parameters.get('session')) is not None
          and session_key == __session_key(key)
          and (data := __session_data(session_key)) is not None):
            flask.g.update = data.get('canUpdate', False)
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
        session_key = __new_session(key, user_data)
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
@__authenticated
def annotated_items(resource_id: str):
    annotation_store = AnnotationStore()
    items = annotation_store.annotated_items(resource_id)
    annotation_store.close()
    return flask.jsonify(items)

#===============================================================================

@annotator_blueprint.route('annotations/<string:resource_id>/<string:item_id>', methods=['GET'])
@__authenticated
def annotations(resource_id: str, item_id: str):
    annotation_store = AnnotationStore()
    items = annotation_store.annotations(resource_id, item_id)
    annotation_store.close()
    return flask.jsonify(items)

#===============================================================================

@annotator_blueprint.route('annotation/<string:annotation_id>', methods=['GET'])
@__authenticated
def annotation(annotation_id: str):
    annotation_store = AnnotationStore()
    annotation = annotation_store.annotation(annotation_id)
    annotation_store.close()
    return flask.jsonify(annotation)

#===============================================================================

@annotator_blueprint.route('annotation/', methods=['POST'])
@__authenticated
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
