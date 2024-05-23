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
from typing import Any, Optional
import uuid

#===============================================================================

import quart            # type: ignore

#===============================================================================

from .pennsieve import get_user
from .server import annotator_blueprint, settings

#===============================================================================
'''
/**
 * A flatmap feature.
 */
export interface MapFeature
{
    id: string
    geometry: {
        type: string
        coordinates: any[]
    }
    properties: Record<any, any>
}

/**
 * Annotation about an item in a resource.
 */
export interface UserAnnotation
{
    resource: string
    item: string
    evidence: URL[]
    comment: string
    feature?: MapFeature
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

/**
 * Information about a logged in user.
 */
export interface UserData {
    name: string
    email: string
    orcid: string
    canUpdate: boolean
}

TEST_USER = {
    'name': 'Test User',
    'email': 'test@example.org',
    'orcid': '0000-0002-1825-0097',
    'canUpdate': True
}

'''
#===============================================================================

ANNOTATION_STORE_SCHEMA = """
    begin;
    create table annotations (resource text, itemid text, item text, created text, orcid text, creator text, annotation text);
    create index annotations_index on annotations(resource, itemid, created, orcid);
    create table features (resource text, itemid text, deleted text, annotation text, feature text);
    create index features_index on features(resource, itemid, deleted);
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

    def annotated_item_ids(self, resource_id: str) -> dict:
    #======================================================
        item_ids = []
        if self.__db is not None:
            item_ids = [row[0]
                        for row in self.__db.execute('''select distinct itemid
                                                        from annotations where resource=?
                                                         order by itemid''', (resource_id, ))
                                            .fetchall()]
        return {
            'resource': resource_id,
            'itemIds': item_ids
        }

    def user_item_ids(self, resource_id: str, user_id: Optional[str], participated: bool) -> dict:
    #=============================================================================================
        item_ids = []
        if self.__db is not None and user_id is not None:
            # Querying participated annotations if participated True, else non-participated annotations
            item_ids = [row[0]
                        for row in self.__db.execute(f'''select distinct itemid from annotations
                                                         where resource=? and orcid {"=" if participated else "!="} ?
                                                         order by itemid''', (resource_id, user_id))
                                            .fetchall()]
        return {
            'resource': resource_id,
            'itemIds': item_ids,
            'userId': user_id,
            'participated': participated,
        }

    def features(self, resource_id: str) -> dict:
    #============================================
        features = []
        if self.__db is not None:
            features = [json.loads(row[0])
                           for row in self.__db.execute('''select feature from features
                                                           where deleted is null and resource=?
                                                           order by itemid''', (resource_id, ))
                                                .fetchall()]
        return {
            'resource': resource_id,
            'features': features
        }

    def item_features(self, resource_id: str, item_ids: list[str]) -> dict:
    #======================================================================
        features = []
        if self.__db is not None and len(item_ids):
            features = [json.loads(row[0])
                for row in self.__db.execute(f'''select feature from features
                                                 where deleted is null and resource=?
                                                       and itemid in ({", ".join("?"*len(item_ids))})
                                                 order by itemid''', (resource_id, *item_ids))
                                    .fetchall()]
        return {
            'resource': resource_id,
            'features': features
        }

    def annotations(self, resource_id: Optional[str]=None, item_id: Optional[str]=None) -> list[dict]:
    #=================================================================================================
        annotations = []
        if self.__db is not None:
            where_values = []
            if resource_id is None:
                where_statement =  ''
            else:
                where_clauses = ['resource=?']
                where_values.append(resource_id)
                if item_id is not None:
                    where_clauses.append('itemid=?')
                    where_values.append(item_id)
                where_statement = 'where ' + ' and '.join(where_clauses)
            for row in self.__db.execute(f'''select rowid, created, creator, annotation, resource, itemid, item
                                        from annotations {where_statement}
                                        order by created desc, creator''',
                                    tuple(where_values)).fetchall():
                annotation = {
                    'annotationId': int(row[0]),
                    'resource': row[4],
                    'item': json.loads(row[6]),
                    'created': row[1],
                    'creator': json.loads(row[2])
                }
                annotation.update(json.loads(row[3]))
                annotations.append(annotation)
        return annotations

    def annotation(self, annotation_id: int) -> dict:
    #================================================
        annotation = {}
        if self.__db is not None:
            row = self.__db.execute('''select a.resource, a.itemid, a.item, a.created, a.creator, a.annotation, f.feature
                                        from annotations as a left join features as f on a.rowid = f.annotation
                                        where a.rowid=? and f.deleted is null''', (annotation_id, )).fetchone()
            if row is not None:
                annotation = {
                    'annotationId': int(annotation_id),
                    'resource': row[0],
                    'item': json.loads(row[2]),
                    'created': row[3],
                    'creator': json.loads(row[4]),
                    'feature': json.loads(row[6]) if row[6] else None,
                }
                annotation.update(json.loads(row[5]))
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
            item = annotation.pop('item', None)
            if not isinstance(item, dict):
                item = {
                    'id': item
                }
            item_id = item['id']
            if (resource_id and item_id
            and creator and (orcid := creator.get('orcid'))):
                creator.pop('canUpdate', None)
                try:
                    feature = annotation.pop('feature', None)
                    cursor = self.__db.cursor()
                    cursor.execute('''insert into annotations
                        (resource, itemid, item, created, orcid, creator, annotation) values (?, ?, ?, ?, ?, ?, ?)''',
                        (resource_id, item_id, json.dumps(item), created, orcid, json.dumps(creator), json.dumps(annotation)))
                    if cursor.lastrowid is not None:
                        result['annotationId'] = int(cursor.lastrowid)
                    # Flag as deleted any non-deleted entries for the feature
                    cursor.execute('''update features set deleted=?
                        where deleted is null and resource=? and itemid=?''',
                        (result['annotationId'], resource_id, item_id))
                    if feature and isinstance(feature, dict):
                        # Add a new row when we have a new feature
                        cursor.execute('''insert into features
                            (resource, itemid, annotation, deleted, feature) values (?, ?, ?, null, ?)''',
                            (resource_id, item_id, result['annotationId'], json.dumps(feature)))
                    cursor.execute('commit')
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

def __authenticated(bearer=False):
    def check_authenticated(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            if quart.request.method == 'GET':
                parameters = quart.request.args
            elif quart.request.method == 'POST':
                parameters = await quart.request.get_json()
            else:
                parameters = {}
            if ((key := parameters.get('key')) is not None
              and (session_key := parameters.get('session')) is not None
              and session_key == __session_key(key)
              and (data := __session_data(session_key)) is not None):
                quart.g.update = data.get('canUpdate', False)
                return await f(*args, **kwargs)
            if bearer and quart.request.method == 'GET' and settings['ANNOTATOR_TOKENS']:
                auth = quart.request.headers.get('Authorization', '')
                if auth.startswith('Bearer '):
                    if auth.split()[1] in settings['ANNOTATOR_TOKENS']:
                        quart.g.update = False
                        return await f(*args, **kwargs)
            response = await quart.make_response('{"error": "forbidden"}', 403)
            return response
        return decorated_function
    return check_authenticated

#===============================================================================

def __get_parameter(name: str, default: Any=None):
    value = quart.request.args.get(name)
    result = json.loads(value) if value is not None else default
    return result

#===============================================================================

@annotator_blueprint.route('authenticate', methods=['GET'])
async def authenticate():
    parameters = quart.request.args
    if (key := parameters.get('key')) is not None:
        user_data = get_user(key)
    else:
        user_data = {'error': 'forbidden'}
    if 'error' not in user_data:
        session_key = __new_session(key, user_data)
        response = await quart.make_response(json.dumps({
            'session': session_key,
            'data': user_data
        }))
    else:
        response = await quart.make_response(json.dumps(user_data), 403)
    response.mimetype = 'application/json'
    return response

#===============================================================================

@annotator_blueprint.route('unauthenticate', methods=['GET'])
async def unauthenticate():
    response = await quart.make_response('{"success": "Unauthenticated"}')
    response.mimetype = 'application/json'
    return response

#===============================================================================

@annotator_blueprint.route('items/', methods=['GET'])
@__authenticated()
async def annotated_items():
    resource_id = __get_parameter('resource')
    user_id = __get_parameter('user')
    annotation_store = AnnotationStore()
    if user_id is not None:
        participated = __get_parameter('participated', True)
        item_ids = annotation_store.user_item_ids(resource_id, user_id, participated)
    else:
        item_ids = annotation_store.annotated_item_ids(resource_id)
    annotation_store.close()
    return quart.jsonify(item_ids)

#===============================================================================

@annotator_blueprint.route('features/', methods=['GET'])
@__authenticated()
async def features():
    resource_id = __get_parameter('resource')
    item_ids = __get_parameter('items')
    annotation_store = AnnotationStore()
    if item_ids is not None:
        if isinstance(item_ids, str):
            item_ids = [item_ids]
        features = annotation_store.item_features(resource_id, item_ids)
    else:
        features = annotation_store.features(resource_id)
    annotation_store.close()
    return quart.jsonify(features)

#===============================================================================

@annotator_blueprint.route('annotations/', methods=['GET'])
@__authenticated()
async def annotations():
    resource_id = __get_parameter('resource')
    item_id = __get_parameter('item')
    annotation_store = AnnotationStore()
    annotations = annotation_store.annotations(resource_id, item_id)
    annotation_store.close()
    return quart.jsonify(annotations)

#===============================================================================

@annotator_blueprint.route('annotation/', methods=['GET'])
@annotator_blueprint.route('annotation/<string:id>', methods=['GET'])
@__authenticated(True)
async def annotation(id: Optional[str]=None):
    annotation_id = __get_parameter('annotation') if id is None else id
    annotation_store = AnnotationStore()
    annotation = annotation_store.annotation(annotation_id)
    annotation_store.close()
    return quart.jsonify(annotation)

#===============================================================================

@annotator_blueprint.route('annotation/', methods=['POST'])
@__authenticated()
async def add_annotation():
    annotation_store = AnnotationStore()
    if quart.request.method == 'POST' and quart.g.update:
        annotation = quart.request.get_json().get('data', {})
        result = annotation_store.add_annotation(annotation)
    else:
        result = '{"error": "forbidden"}', 403, {'mimetype': 'application/json'}
    annotation_store.close()
    return quart.jsonify(result)

#===============================================================================
#===============================================================================

@annotator_blueprint.route('download/', methods=['GET'])
@__authenticated(True)
async def download():
    annotation_store = AnnotationStore()
    annotations = annotation_store.annotations()
    annotation_store.close()
    return quart.jsonify(annotations)

#===============================================================================
#===============================================================================
