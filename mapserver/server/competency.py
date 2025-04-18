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
"""

See ../docs/competency.rst

"""
#===============================================================================

from litestar import get, post, Request, Router

#===============================================================================

from ..competency import query, query_definition, query_definitions
from ..competency.definition import QueryDefinitionDict, QueryDefinitionSummary, QueryRequest

#===============================================================================

@get('queries')
async def competency_query_definitions(request: Request) -> list[QueryDefinitionSummary]:
#=======================================================================================
    return await query_definitions(request)

@get('queries/{query_id:str}')
async def competency_query_definition(query_id: str, request: Request) -> QueryDefinitionDict:
#=============================================================================================
    return await query_definition(query_id, request)

@post('query/')
async def competency_query(data: QueryRequest, request: Request) -> dict:
#=======================================================================
    return await query(data, request)

#===============================================================================
#===============================================================================

competency_router = Router(
    path="/competency",
    route_handlers=[
        competency_query,
        competency_query_definition,
        competency_query_definitions,
    ]
)

#===============================================================================
