#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-25  David Brooks
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

from contextlib import asynccontextmanager
import importlib.resources
import os
from typing import AsyncGenerator, Optional

#===============================================================================

import asyncpg
from litestar import exceptions, Litestar, Request

#===============================================================================

from .definition import load_query_definitions
from .definition import QueryDefinitionDict, QueryDefinitionSummary, QueryRequest
from .definition import QueryError, QueryResults

#===============================================================================

COMPETENCY_DATABASE = 'map-knowledge'

COMPETENCY_USER = os.environ.get('COMPETENCY_USER', 'abi:knowledge')
COMPETENCY_HOST = os.environ.get('COMPETENCY_HOST', 'localhost:5432')

if not COMPETENCY_USER:
    print('Competency queries are unavailable because COMPETENCY_USER is not set')

#===============================================================================
#===============================================================================

QUERY_DEFINITIONS = str(importlib.resources.files() / 'data' / 'queries.yaml')

def get_query_definitions(app: Litestar):
#========================================
    query_definitions = getattr(app.state, 'competency-definitions', None)
    if query_definitions is None:
        query_definitions = load_query_definitions(QUERY_DEFINITIONS)
        app.state['competency-definitions'] = query_definitions
    return query_definitions

def initialise_query_definitions(app: Litestar):
#===============================================
    get_query_definitions(app)

#===============================================================================
#===============================================================================

@asynccontextmanager
async def competency_connection_context(app: Litestar) -> AsyncGenerator[None, None]:
#====================================================================================
    competency_pool = getattr(app.state, 'competency-pool', None)
    if competency_pool is None and COMPETENCY_USER:
        try:
            competency_pool = await asyncpg.create_pool(
                dsn=f'postgresql://{COMPETENCY_USER}@{COMPETENCY_HOST}/{COMPETENCY_DATABASE}',
                timeout=5
            )
            app.state['competency-pool'] = competency_pool
        except Exception as err:
            # log (where?)
            print(f'Unable to connect to competency database: {COMPETENCY_HOST}/{COMPETENCY_DATABASE}')
            print(f'Exception: {err}')
            pass
    try:
        yield
    finally:
        if competency_pool is not None:
            await competency_pool.close()

def get_competency_pool(app: Litestar) -> Optional[asyncpg.Pool]:
#================================================================
    return getattr(app.state, 'competency-pool', None)

#===============================================================================
#===============================================================================

async def query_definition(query_id: str, request: Request) -> QueryDefinitionDict:
#==================================================================================
    definition = get_query_definitions(request.app).get(query_id)
    if definition is None:
        raise exceptions.NotFoundException(detail=f'Unknown competency query: {query_id}')
    return definition.as_dict


async def query_definitions(request: Request) -> list[QueryDefinitionSummary]:
#=============================================================================
    definitions = get_query_definitions(request.app)
    return [defn.summary for defn in definitions.values()]


async def query(data: QueryRequest, request: Request) -> QueryResults|QueryError:
#================================================================================
    if (defn := get_query_definitions(request.app).get(data['query_id'])) is None:
        return {'error': f"Unknown query ID: {data['query_id']}"}
    try:
        (sql, params) = defn.make_sql(data)
    except ValueError as err:
        return {'error': f'Error building query: {err}'}
    if (pool := get_competency_pool(request.app)) is None:
        return {'error': 'Backend cannot connect to Competency database'}
    try:
        async with pool.acquire() as connection:
            records = await connection.fetch(sql, *params)
            value_rows: list[list[str]] = []
            for record in records:
                value_rows.append([record.get(key)
                                    for key in defn.result_keys])
            return {
                'query_id': data['query_id'],
                'results': {
                    'keys': defn.result_keys,
                    'values': value_rows
                }
            }
    except Exception as err:
        return {'error': f'Error executing query: {err}'}

#===============================================================================
