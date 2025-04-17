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

from litestar import post, Request, Router

#===============================================================================

from ..competency import query as competency_query
from ..competency.definition import QueryRequest

#===============================================================================

@post('query/')
async def query(data: QueryRequest, request: Request) -> dict:
#=============================================================
    """
    Query the flatmap server's knowledge base.

    :<json string sql: SQL code to execute
    :<jsonarr string params: any parameters for the query

    :>json array(string) keys: column names of result values
    :>json array(array(string)) values: result data rows
    :>json string error: any error message
    """
    return await competency_query(data, request)

#===============================================================================
#===============================================================================

competency_router = Router(
    path="/competency",
    route_handlers=[
        query,
    ]
)

#===============================================================================
