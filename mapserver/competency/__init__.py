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
from litestar import Litestar, Request

#===============================================================================

from .definition import load_query_definitions, QueryRequest

#===============================================================================

COMPETENCY_DATABASE = 'map-knowledge'

COMPETENCY_USER = os.environ.get('COMPETENCY_USER')
COMPETENCY_USER = 'abi:knowledge'
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

async def query(data: QueryRequest, request: Request) -> dict:
#=============================================================

    if (pool := get_competency_pool(request.app)) is None:
        ## 40X error
        ## log??
        ## or just return 'error' in response...
        return {}

    if (defn := get_query_definitions(request.app).get(data.query_id)) is None:
        pass
        # 403 ?
        # log/print
        ## or just return 'error' in response...
        return {}

    (sql, params) = defn.make_sql(data)

    async with pool.acquire() as connection:
        # Open a transaction.
        ## Is a transaction needed ??
        #
        async with connection.transaction():
            result = await connection.execute(sql, params)

    return {}

#===============================================================================
