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
from dataclasses import dataclass
import os
from typing import AsyncGenerator, Optional

#===============================================================================

import asyncpg
from litestar import Litestar, Request

#===============================================================================

COMPETENCY_DATABASE = 'map-knowledge'

COMPETENCY_USER = os.environ.get('COMPETENCY_USER')
COMPETENCY_USER = 'abi:knowledge'
COMPETENCY_HOST = os.environ.get('COMPETENCY_HOST', 'localhost:5432')

if not COMPETENCY_USER:
    print('Competency queries are unavailable because COMPETENCY_USER is not set')

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

def get_competency_pool(request: Request) -> Optional[asyncpg.Pool]:
#===================================================================
    return getattr(request.app.state, 'competency-pool', None)

#===============================================================================
