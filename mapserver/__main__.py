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
import signal
from typing import Any

#===============================================================================

from hypercorn.asyncio import serve
from hypercorn.config import Config

#===============================================================================

from .server import app, initialise, map_maker

#===============================================================================

__shutdown_event = asyncio.Event()

def __signal_handler(*_: Any) -> None:
#=====================================
    __shutdown_event.set()
    if map_maker is not None:
        map_maker.terminate()

def main(viewer=False):
#======================
    initialise(viewer)
    config = Config()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, __signal_handler)
    loop.run_until_complete(
        serve(app, config, shutdown_trigger=__shutdown_event.wait)
    )

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
