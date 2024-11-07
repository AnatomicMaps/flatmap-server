#===============================================================================
#
#  Flatmap server
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

from dataclasses import dataclass
import os
from typing import Optional

#===============================================================================

from litestar import get, MediaType, post, Request, Router
from litestar.response import File

#===============================================================================

from ..knowledge import KnowledgeStore
from ..knowledge.hierarchy import CACHED_SPARC_HIERARCHY
from ..settings import settings

#===============================================================================
#===============================================================================

@dataclass
class QueryData:
    sql: str
    params: Optional[list[str]]

#===============================================================================
#===============================================================================

def query_knowledge(sql: str, params: list[str]) -> dict:
#========================================================
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'])
    result = knowledge_store.query(sql, params) if knowledge_store else {
                'error': 'Knowledge Store not available'
             }
    knowledge_store.close()
    return result

def get_knowledge_sources() -> list[str]:
#========================================
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'])
    sources = knowledge_store.knowledge_sources() if knowledge_store else []
    knowledge_store.close()
    return sources

#===============================================================================
#===============================================================================

@post('query/')
async def knowledge_query(data: QueryData, request: Request) -> dict:
#====================================================================
    """
    Query the flatmap server's knowledge base.

    :<json string sql: SQL code to execute
    :<jsonarr string params: any parameters for the query

    :>json array(string) keys: column names of result values
    :>json array(array(string)) values: result data rows
    :>json string error: any error message
    """
    result = query_knowledge(data.sql, data.params if data.params is not None else [])
    if 'error' in result:
        request.logger.warning(f'SQL: {result["error"]}')
    return result

@get('sources')
async def knowledge_sources() -> dict:
#=====================================
    """
    Return the knowledge sources available in the server's knowledge store.

    :>json array(string) sources: a list of knowledge sources. The list is
                                  in descending order, with the most recent
                                  source at the beginning
    """
    sources = get_knowledge_sources()
    return {'sources': sources}

@get('sparcterms')
async def sparcterms() -> File:
#==============================
    filename = os.path.join(settings['FLATMAP_ROOT'], CACHED_SPARC_HIERARCHY)
    return File(path=filename, media_type=MediaType.JSON)

@get('schema-version')
async def knowledge_schema_version(request: Request) -> dict:
#============================================================
    """
    :>json number version: the version of the store's schema
    """
    result = query_knowledge('select value from metadata where name=?', ['schema_version'])
    if 'error' in result:
        request.logger.warning(f'SQL: {result["error"]}')
    return {'version': result['values'][0][0]}

#===============================================================================
#===============================================================================

knowledge_router = Router(
    path="/knowledge",
    route_handlers=[
        knowledge_query,
        knowledge_schema_version,
        knowledge_sources,
        sparcterms
    ]
)

#===============================================================================
