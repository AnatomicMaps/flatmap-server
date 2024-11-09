#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2020 - 2024 David Brooks
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

import asyncio
import logging.config
import os
import sys

#===============================================================================

from hypercorn.asyncio import serve
from hypercorn.config import Config
import yaml

#===============================================================================

from .server import app  ## , initialise
from .settings import settings

#===============================================================================

SERVER_INTERFACE = os.environ.get('SERVER_INTERFACE', '127.0.0.1')
SERVER_PORT      = os.environ.get('SERVER_PORT', '8000')

#===============================================================================

LOGGING_CONFIG = '''
version: 1
disable_existing_loggers: False
formatters:
  standard:
    format: '%(asctime)s %(levelname)s: %(message)s'
  simple:
    format: '%(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: standard
    stream: 'ext://sys.stdout'
  rotatingAccessHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: simple
    filename: {ACCESS_LOG}
    maxBytes: 1048576       # 1 MB
    backupCount: 9
  rotatingErrorHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: standard
    filename: {ERROR_LOG}
    maxBytes: 1048576       # 1 MB
    backupCount: 9
  rotatingLitestarHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: standard
    filename: {LITESTAR_LOG}
    maxBytes: 1048576       # 1 MB
    backupCount: 9
root:
  handlers:
  - console
  level: INFO
  propagate: False
loggers:
  hypercorn.access:
    handlers:
    - rotatingAccessHandler
    level: INFO
    propagate: False
  hypercorn.error:
    handlers:
    - rotatingErrorHandler
    - console
    level: INFO
    propagate: False
  litestar:
    handlers:
    - rotatingLitestarHandler
    - console
    level: INFO
    propagate: False
'''

#===============================================================================

def configure_logging(access_log: str, error_log: str, litestar_log: str):
    config = LOGGING_CONFIG.format(ACCESS_LOG=access_log, ERROR_LOG=error_log, LITESTAR_LOG=litestar_log)
    logging.config.dictConfig(yaml.safe_load(config))

#===============================================================================

async def run_server(viewer=False):
#==================================
    # Save viewer state for server initialisation
    settings['MAP_VIEWER'] = viewer

    ACCESS_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'access_log')
    ERROR_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'error_log')
    LITESTAR_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'maker_log')
    configure_logging(ACCESS_LOG_FILE, ERROR_LOG_FILE, LITESTAR_LOG_FILE)

    config = Config()
    config.accesslog = logging.getLogger('hypercorn.access')
    config.errorlog = logging.getLogger('hypercorn.error')

    config.bind = [f'{SERVER_INTERFACE}:{SERVER_PORT}']
    asyncio.run(
        serve(app, config)
    )

#===============================================================================

def main(viewer=False):
#======================
    try:
        asyncio.run(run_server(viewer))
    except KeyboardInterrupt:
        pass

#===============================================================================

if __name__ == '__main__':
#=========================
    main(len(sys.argv) > 1 and sys.argv[1] == 'viewer')

#===============================================================================
