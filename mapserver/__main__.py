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

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

#===============================================================================

from .server import server, viewer

#===============================================================================

def run_app(app):
    fastapi = FastAPI()
    fastapi.add_middleware(CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"])
    fastapi.mount('/', WSGIMiddleware(app))
    uvicorn.run(fastapi, access_log=False)

def mapserver():
    run_app(server())

def mapviewer():
    run_app(viewer())

#===============================================================================

if __name__ == '__main__':
    mapserver()

#===============================================================================
