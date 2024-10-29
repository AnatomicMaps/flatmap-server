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

import gzip
import io
import json
import os
import os.path
import pathlib
import sqlite3
import sys
from typing import Optional

#===============================================================================

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import RapidocRenderPlugin

#===============================================================================

from ..knowledge import KnowledgeStore
from ..settings import settings
from .. import __version__

from .annotator import annotator_router
from .connectivity import connectivity_router
from .flatmap import flatmap_router
from .knowledge import knowledge_router
from .maker import maker_router, initialise as init_maker, map_maker
from .viewer import viewer_router

#===============================================================================

cors_config = CORSConfig(allow_origins=["*"])

app = Litestar(
    route_handlers=[
        annotator_router,
        connectivity_router,
        flatmap_router,
        knowledge_router,
        maker_router,
        viewer_router
    ],
    cors_config=cors_config,
    openapi_config=OpenAPIConfig(
        title="Flatmap Server Web API",
        version=__version__,
        render_plugins=[RapidocRenderPlugin()],
    ),
)

#===============================================================================
#===============================================================================

def initialise(viewer=False):
    if viewer and not os.path.exists(settings['FLATMAP_VIEWER']):
        exit(f'Missing {settings["FLATMAP_VIEWER"]} directory -- set FLATMAP_VIEWER environment variable to the full path')
    settings['MAP_VIEWER'] = viewer
    app.logger.info(f'Starting flatmap server version {__version__}')
    print(f'Starting flatmap server version {__version__}')
    if not settings['MAPMAKER_TOKENS']:
        # Only warn once...
        app.logger.warning('No bearer tokens defined')

    # Try opening our knowledge base
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'], create=True)
    if knowledge_store.error is not None:
        app.logger.error('{}: {}'.format(knowledge_store.error, knowledge_store.db_name))
    knowledge_store.close()

    init_maker()

#===============================================================================
#===============================================================================
