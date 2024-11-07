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
import os
import signal
import sys
from typing import Any

#===============================================================================

from hypercorn.asyncio import serve

import uvloop

#===============================================================================

from .server import app, initialise
from .server.maker import map_maker
from .settings import config, settings

SERVER_INTERFACE = os.environ.get('SERVER_INTERFACE', '127.0.0.1')
SERVER_PORT      = os.environ.get('SERVER_PORT', '8000')

#===============================================================================

class SyncLogger:
    def __init__(self, logger):
        self.__logger = logger

    def critical(self, msg, *args, **kwds):
        asyncio.run(self.__logger.critical(msg, *args, **kwds))

    def debug(self, msg, *args, **kwds):
        asyncio.run(self.__logger.debug(msg, *args, **kwds))

    def error(self, msg, *args, **kwds):
        asyncio.run(self.__logger.error(msg, *args, **kwds))

    def exception(self, msg, *args, **kwds):
        asyncio.run(self.__logger.exception(msg, *args, **kwds))

    def info(self, msg, *args, **kwds):
        asyncio.run(self.__logger.info(msg, *args, **kwds))

    def log(self, msg, *args, **kwds):
        asyncio.run(self.__logger.log(msg, *args, **kwds))

    def warning(self, msg, *args, **kwds):
        asyncio.run(self.__logger.warning(msg, *args, **kwds))

#===============================================================================

__shutdown_event = asyncio.Event()

def __signal_handler(*_: Any) -> None:
#=====================================
    print('Shutting down...')
    __shutdown_event.set()
    if map_maker is not None:
        map_maker.terminate()

## NB. We initialise logging and run the event log this particular way in order
##     to catch exceptions and capture all log messages

async def runserver(viewer=False):
#=================================
    config.accesslog = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'access_log')
    config.errorlog = os.path.join(settings['FLATMAP_SERVER_LOGS'], 'error_log')
    settings['LOGGER'] = config.log

    ## NB. This currently works but might break with a ``quart`` upgrade
    ##
    ## We need to better initialise logging, using ``logging.config.dictConfig``
    ##
    app.logger = SyncLogger(config.log)

    initialise(viewer)

    uvloop.install()
    config.worker_class = 'uvloop'
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, __signal_handler)
    loop.add_signal_handler(signal.SIGTERM, __signal_handler)

    config.bind = [f'{SERVER_INTERFACE}:{SERVER_PORT}']
    print(f'Running on {config.bind[0]} (CTRL + C to quit)')

    loop.run_until_complete(
        serve(app, config, shutdown_trigger=__shutdown_event.wait)
    )

#===============================================================================

def main(viewer=False):
#======================
    try:
        asyncio.run(runserver(viewer))
    except KeyboardInterrupt:
        pass

def mapserver():
#===============
    main()

def mapviewer():
#===============
    main(True)

#===============================================================================

if __name__ == '__main__':
#=========================
    main(len(sys.argv) > 1 and sys.argv[1] == 'viewer')

#===============================================================================
