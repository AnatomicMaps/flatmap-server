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

import json
import os
import subprocess
import sys
import yaml

#===============================================================================

from .server import app
from .settings import settings

#===============================================================================

SERVER_INTERFACE = os.environ.get('SERVER_INTERFACE', '127.0.0.1')
SERVER_PORT      = os.environ.get('SERVER_PORT', '8000')

# Make available to other modules
settings['SERVER_PORT'] = SERVER_PORT

#===============================================================================

LOGGING_CONFIG = '''
version: 1
disable_existing_loggers: False
formatters:
  simple:
    format: '%(message)s'
  standard:
    format: '%(asctime)s %(levelname)s: %(message)s'
  generic:
    format: '%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] %(message)s'
    datefmt: '[%Y-%m-%d %H:%M:%S'
  access:
    format: '%(message)s'
    datefmt: '[%Y-%m-%d %H:%M:%S %z]'
handlers:
  console:
    class: logging.StreamHandler
    formatter: generic
    stream: 'ext://sys.stdout'
  rotatingAccessHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: access
    filename: {ACCESS_LOG}
    maxBytes: 4194304       # 4 MB
    backupCount: 9
  rotatingErrorHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: generic
    filename: {ERROR_LOG}
    maxBytes: 1048576       # 1 MB
    backupCount: 9
  rotatingLitestarHandler:
    class: logging.handlers.RotatingFileHandler
    formatter: generic
    filename: {LITESTAR_LOG}
    maxBytes: 1048576       # 1 MB
    backupCount: 9
root:
  handlers:
  - console
  level: INFO
  propagate: False
loggers:
  _granian:
    handlers:
    - rotatingErrorHandler
    - console
    level: INFO
    propagate: False
  granian.access:
    handlers:
    - rotatingAccessHandler
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

def configure_logging(access_log: str, error_log: str, litestar_log: str) -> str:
    config = LOGGING_CONFIG.format(ACCESS_LOG=access_log, ERROR_LOG=error_log, LITESTAR_LOG=litestar_log)
    log_config = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'log-config.json')
    with open(log_config, 'w') as fp:
        json.dump(yaml.safe_load(config), fp)
    return log_config

#===============================================================================

def run_server(viewer: bool=False):
#==================================
    # Save viewer state for server initialisation
    os.environ['MAP_VIEWER'] = 'VIEWER' if viewer else ''

    ACCESS_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'access_log')
    ERROR_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'error_log')
    LITESTAR_LOG_FILE = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'maker_log')
    log_config = configure_logging(ACCESS_LOG_FILE, ERROR_LOG_FILE, LITESTAR_LOG_FILE)

    subprocess.run(['granian',
        '--interface', 'asgi',
        '--host', SERVER_INTERFACE,
        '--port', SERVER_PORT,
        '--log',
        '--log-config', log_config,
        '--access-log',
        'mapserver.__main__:app'])

#===============================================================================

def main(viewer=False):
#======================
    try:
        run_server(viewer)
    except KeyboardInterrupt:
        pass

#===============================================================================

if __name__ == '__main__':
#=========================
    main(len(sys.argv) > 1 and sys.argv[1] == 'viewer')

#===============================================================================
