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

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import pathlib
import sqlite3
from typing import Any, Optional
import uuid

#===============================================================================

from litestar import exceptions, get, post, Request, Response, Router
from litestar.middleware.session.server_side import ServerSideSessionConfig

#===============================================================================

if __name__ != '__main__':
    from ..pennsieve import get_user as get_pennsieve_user
    from ..settings import settings
else:
    settings = {}

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

SCHEMA_VERSION = '1.1'

ANNOTATION_STORE_SCHEMA = """
    begin;
    create table metadata (name text primary key, value text);
    create table annotations (id text primary key, resource text, itemid text, item text, created text, orcid text, creator text, annotation text, status text);
    create index annotations_index on annotations(resource, itemid, created, orcid);
    create table features (resource text, itemid text, deleted text, annotation text, feature text);
    create index features_index on features(resource, itemid, deleted);
    create index features_annotation_index on features(annotation, resource, itemid, deleted);
    insert into metadata (name, value) values ('schema_version', '{SCHEMA_VERSION}');
    commit;
"""

SCHEMA_UPGRADES: dict[Optional[str], tuple[str, str]] = {
    None: ('1.1', """
        alter table annotations add id text;
        alter table annotations add status text;
        create index features_annotation_index on features(annotation, resource, itemid, deleted);
        update annotations set id = rowid;
        create table metadata (name text primary key, value text);
        replace into metadata (name, value) values ('schema_version', '1.1');
    """)
}

#===============================================================================

class AnnotationStore:
    def __init__(self, db_path: Optional[pathlib.Path]=None):
        if db_path is None:
            db_path = pathlib.Path(settings['FLATMAP_ROOT']) / 'annotation_store.db'
        # Create annotation store if it doesn't exist
        db_name = db_path.resolve()
        if not db_name.exists():
            db = sqlite3.connect(db_name)
            db.executescript(ANNOTATION_STORE_SCHEMA)
            db.close()
        self.__db = sqlite3.connect(db_name)

    @property
    def db(self):
        return self.__db

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
            for row in self.__db.execute(f'''select id, created, creator, annotation, resource, itemid, item, status
                                        from annotations {where_statement}
                                        order by created desc, creator''',
                                    tuple(where_values)).fetchall():
                annotation = {
                    'annotationId': row[0],
                    'resource': row[4],
                    'item': json.loads(row[6]),
                    'created': row[1],
                    'creator': json.loads(row[2]),
                    'status': row[7]
                }
                annotation.update(json.loads(row[3]))
                annotations.append(annotation)
        return annotations

    def annotation(self, annotation_id: str) -> dict:
    #================================================
        annotation = {}
        if self.__db is not None:
            row = self.__db.execute('''select a.resource, a.itemid, a.item, a.created, a.creator, a.annotation, a.status, f.feature
                                        from annotations as a left join features as f on a.id = f.annotation
                                        where a.id=? and f.deleted is null''', (annotation_id, )).fetchone()
            if row is not None:
                annotation = {
                    'annotationId': annotation_id,
                    'resource': row[0],
                    'item': json.loads(row[2]),
                    'created': row[3],
                    'creator': json.loads(row[4]),
                    'status': row[6],
                    'feature': json.loads(row[7]) if row[7] else None,
                }
                annotation.update(json.loads(row[5]))
        return annotation

    def add_annotation(self, annotation: dict) -> dict[str, Any]:
    #============================================================
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
                    status = annotation.pop('status', None)
                    annotation_id = str(uuid.uuid4)
                    result['annotationId'] = annotation_id
                    cursor = self.__db.cursor()
                    cursor.execute('''insert into annotations
                        (id, resource, itemid, item, created, orcid, creator, annotation, status) values (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (annotation_id, resource_id, item_id, json.dumps(item), created, orcid,
                         json.dumps(creator), json.dumps(annotation), status))
                    # Flag as deleted any non-deleted entries for the feature
                    cursor.execute('''update features set deleted=?
                        where deleted is null and resource=? and itemid=?''',
                        (annotation_id, resource_id, item_id))
                    if feature and isinstance(feature, dict):
                        # Add a new row when we have a new feature
                        cursor.execute('''insert into features
                            (resource, itemid, annotation, deleted, feature) values (?, ?, ?, null, ?)''',
                            (resource_id, item_id, annotation_id, json.dumps(feature)))
                    cursor.execute('commit')
                except sqlite3.OperationalError as err:
                    result['error'] = str(err)
        else:
            result['error'] = 'No annotation database...'
        return result

    def update_status(self, annotation_id: str, status: str) -> dict[str, Any]:
    #==========================================================================
        result = {}
        if self.__db is not None:
            try:
                cursor = self.__db.cursor()
                cursor.execute('update annotations set status=? where id=', (annotation_id, status))
                result['success'] = 'status updated'
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
#===============================================================================

def __authenticated_session(query: dict[str, Any], request: Request) -> bool:
#============================================================================
    request.session['update'] = False
    if ((key := query.get('key')) is not None
      and (session_key := query.get('session')) is not None
      and session_key == __session_key(key)
      and (data := __session_data(session_key)) is not None):
        request.session['update'] = data.get('canUpdate', False)
        return True
    return False

def __authenticated_bearer(request: Request) -> bool:
#====================================================
    if request.method == 'GET' and settings['ANNOTATOR_TOKENS']:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            if auth.split()[1] in settings['ANNOTATOR_TOKENS']:
                request.session['update'] = auth.split()[1] in settings['ANNOTATOR_UPDATE']
                return True
    return False

#===============================================================================

@get('authenticate')
async def authenticate(query: dict[str, Any]) -> dict|Response:
    if (key := query.get('key')) is not None:
        user_data = get_pennsieve_user(key)     # type: ignore
        if 'error' not in user_data:
            session_key = __new_session(key, user_data)
            response = {
                'session': session_key,
                'data': user_data
            }
        else:
            response = Response(content=user_data, status_code=403)
    else:
        response = Response(content={'error': 'forbidden'}, status_code=403)
    return response

#===============================================================================

@get('unauthenticate')
async def unauthenticate(query: dict[str, Any], request: Request) -> dict:
    if (session := query.get('session')) is not None:
        __del_session(session)
        request.session['update'] = False
    return {"success": "Unauthenticated"}

#===============================================================================

@get('items/')
async def annotated_items(query: dict[str, Any], request: Request) -> dict:
    if __authenticated_session(query, request):
        if (resource_id := query.get('resource')) is not None:
            user_id = query.get('user')
            annotation_store = AnnotationStore()
            if user_id is not None:
                participated = query.get('participated', True)
                item_ids = annotation_store.user_item_ids(resource_id, user_id, participated)
            else:
                item_ids = annotation_store.annotated_item_ids(resource_id)
            annotation_store.close()
            return item_ids
        return {}
    raise exceptions.NotAuthorizedException()

#===============================================================================

@get('features/')
async def features(query: dict[str, Any], request: Request) -> dict:
    if __authenticated_session(query, request):
        if (resource_id := query.get('resource')) is not None:
            annotation_store = AnnotationStore()
            if (item_ids := query.get('items')) is not None:
                if isinstance(item_ids, str):
                    item_ids = [item_ids]
                features = annotation_store.item_features(resource_id, item_ids)
            else:
                features = annotation_store.features(resource_id)
            annotation_store.close()
            return features
        return {}
    raise exceptions.NotAuthorizedException()

#===============================================================================

@get('annotations/')
async def annotations(query: dict[str, Any], request: Request) -> list[dict]:
    if __authenticated_session(query, request):
        if ((resource_id := query.get('resource')) is not None
        and (item_id := query.get('item')) is not None):
            annotation_store = AnnotationStore()
            annotations = annotation_store.annotations(resource_id, item_id)
            annotation_store.close()
            return annotations
        return []
    raise exceptions.NotAuthorizedException()

#===============================================================================

@get(['annotation/', 'annotation/<str:id>'])
async def annotation(query: dict[str, Any], request: Request, id: Optional[str]=None) -> dict:
    if __authenticated_session(query, request):
        annotation_id = query.get('annotation', '') if id is None else id
        annotation_store = AnnotationStore()
        annotation = annotation_store.annotation(annotation_id)
        annotation_store.close()
        return annotation
    raise exceptions.NotAuthorizedException()

#===============================================================================

@dataclass
class AnnotationUpdateRequest:
    key: str
    session: str
    data: dict

#===============================================================================

@post('annotation/')
async def add_annotation(data: AnnotationUpdateRequest, request: Request) -> dict|Response:
    if __authenticated_session(dataclasses.asdict(data), request):
        if request.session['update']:
            annotation_store = AnnotationStore()
            result = annotation_store.add_annotation(data.data)
            annotation_store.close()
        else:
            result = Response(content={'error': 'forbidden'}, status_code=403)
        return result
    raise exceptions.NotAuthorizedException()

#===============================================================================

@post('update/')
async def update_status(data: AnnotationUpdateRequest, request: Request) -> dict|Response:
    if __authenticated_session(dataclasses.asdict(data), request) or __authenticated_bearer(request):
        if request.session['update']:
            annotation_store = AnnotationStore()
            annotation_id = data.data.get('annotationId')
            status = data.data.get('status')
            if annotation_id is not None and status is not None:
                result = annotation_store.update_status(annotation_id, status)
            else:
                result = Response(content={'error': 'invalid parameters'}, status_code=400)
            annotation_store.close()
        else:
            result = Response(content={'error': 'forbidden'}, status_code=403)
        return result
    raise exceptions.NotAuthorizedException()

#===============================================================================

@get('download/')
async def download(request: Request)  -> list[dict]:
    if __authenticated_bearer(request):
        annotation_store = AnnotationStore()
        annotations = annotation_store.annotations()
        annotation_store.close()
        return annotations
    raise exceptions.NotAuthorizedException()

#===============================================================================
#===============================================================================

annotator_router = Router(
    path="/annotator",
    route_handlers=[
        add_annotation,
        annotated_items,
        annotations,
        annotation,
        authenticate,
        download,
        features,
        unauthenticate
        ],
        middleware=[ServerSideSessionConfig().middleware],
        include_in_schema=False
    )

#===============================================================================
#===============================================================================

if __name__ == '__main__':
    import logging

    store = AnnotationStore(pathlib.Path('flatmaps/annotation_store.db'))
    if store.db is not None:
        schema_version: Optional[str] = None
        row = store.db.execute("select name from sqlite_schema where type='table' and name='metadata'").fetchone()
        if row is not None:
            row = store.db.execute("select value from metadata where name='schema_version").fetchone()
            if row is not None:
                schema_version = row[0]
        if schema_version != SCHEMA_VERSION:
            while schema_version != SCHEMA_VERSION:
                if (upgrade := SCHEMA_UPGRADES.get(schema_version)) is None:
                    raise ValueError(f'Unable to upgrade annotation schema from version {schema_version}')
                logging.warn(f'Upgrading annotation schema from version {schema_version} to {upgrade[0]}')
                schema_version = upgrade[0]
                try:
                    store.db.executescript(upgrade[1])
                except sqlite3.Error as e:
                    store.db.rollback()
                    raise ValueError(f'Unable to upgrade annotation schema to version {schema_version}: {str(e)}')
                store.db.commit()

#===============================================================================
#===============================================================================
