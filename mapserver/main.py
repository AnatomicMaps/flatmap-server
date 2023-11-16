#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019  David Brooks
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


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

import uvicorn.server
#===============================================================================

from .server import server, viewer
from .settings import settings

#===============================================================================

def configure_logging():
    settings['LOGGER'] = uvicorn.server.logger

def fastapi(flask_app):
    app = FastAPI()
    app.add_middleware(CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"])
    app.mount('/', WSGIMiddleware(flask_app))
    return app

def mapserver():
    configure_logging()
    return fastapi(server())

def mapviewer():
    configure_logging()
    return fastapi(viewer())

#===============================================================================

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(mapserver())

#===============================================================================
