#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2020  David Brooks
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

import dataclasses
from dataclasses import dataclass
import asyncio
import json
import logging
import multiprocessing
import os
import queue
import sys
import threading
from typing import Any, Optional
import uuid

#===============================================================================

import uvloop

#===============================================================================

from ..settings import settings

from mapmaker import MapMaker
import mapmaker.utils as utils

#===============================================================================

"""
If a file with this name exists in the map's output directory then the map
is in the process of being made
"""
MAKER_SENTINEL = '.map_making'

#===============================================================================

MAKER_RESULT_KEYS = ['id', 'models', 'uuid']

#===============================================================================

@dataclass
class MakerData:
    source: str
    manifest: str
    commit: Optional[str] = None
    force: Optional[bool] = None

@dataclass
class MakerStatus:
    id: int
    status: str
    pid: Optional[int]

@dataclass
class MakerResponse(MakerStatus):
    source: str
    commit: Optional[str] = None

@dataclass
class MakerLogResponse(MakerStatus):
    log: str
    stamp: Optional[str] = None

#===============================================================================

def log_file(pid):
    return os.path.join(settings['MAPMAKER_LOGS'], f'{pid}.log.json')

#===============================================================================

def _run_in_loop(func, args):
    loop = uvloop.new_event_loop()
    loop.run_until_complete(func(args))

async def _make_map(params):
#===========================
    try:
        mapmaker = MapMaker(params)
        mapmaker.make()
    except Exception as err:
        utils.log.exception(err, exc_info=True)
        sys.exit(1)

#===============================================================================

class MakerProcess(multiprocessing.Process):
    def __init__(self, params: dict[str, Any]):
        id = str(uuid.uuid4())
        self.__log_queue = multiprocessing.Queue()
        params['logQueue'] = self.__log_queue      ## Is there a better name...
        super().__init__(target=_run_in_loop, args=(_make_map, params), name=id)
        self.__id = id
        self.__process_id = None
        self.__log_file = None
        self.__status = 'queued'
        self.__result = {}

    @property
    def completed(self):
        return self.__status in ['terminated', 'aborted']

    @property
    def log_file(self):
        return self.__log_file

    @property
    def id(self):
        return self.__id

    @property
    def process_id(self):
        return self.__process_id

    @property
    def result(self):
        return self.__result

    @property
    def status(self) -> str:
        return self.__status
    @status.setter
    def status(self, value: str):
        self.__status = value

    def close(self):
    #===============
        self.__clean_up()
        if self.exitcode == 0:
            self.__status = 'terminated'
        else:
            self.__status = 'aborted'
        super().join()
        super().close()

    def get_log(self, start_line=1) -> str:
    #======================================
        if (filename := self.__log_file) is not None and os.path.exists(filename):
            with open(filename) as fp:
                log_lines = fp.read().split('\n')
                return '\n'.join(log_lines[start_line-1:])
        return ''

    def __clean_up(self):
    #====================
        if 'uuid' in self.__result:
            # Remove the log file when we've succesfully built a map
            # (it's already been copied into the map's directory)
            if self.__log_file is not None:
                os.remove(self.__log_file)
                self.__log_file = None

    def read_log_queue(self) -> Optional[dict]:
    #==========================================
        try:
            log_record = self.__log_queue.get(block=False)
            message = json.loads(log_record.msg)
            if log_record.levelno == logging.CRITICAL:
                if message['msg'].startswith('Mapmaker succeeded'):
                    self.__result = { key: value for key in MAKER_RESULT_KEYS
                                        if (value := message.get(key)) is not None }
            return message
        except queue.Empty:
            pass

    def start(self):
    #===============
        self.__status = 'running'
        super().start()
        self.__process_id = self.pid
        self.__log_file = log_file(self.pid)

#===============================================================================

class Manager(threading.Thread):
    """A thread to manage flatmap generation"""
    def __init__(self):
        super().__init__(name='maker-thread')
        self.__log = settings['LOGGER']
        self.__map_dir = None
        self.__processes_by_id: dict[str, MakerProcess] = {}
        self.__running_processes: list[str] = []
        self.__queued_processes:queue.Queue[MakerProcess] = queue.Queue()

        # Make sure we have a directory for log files
        if not os.path.exists(settings['MAPMAKER_LOGS']):
            os.makedirs(settings['MAPMAKER_LOGS'])
        self.__map_dir = settings['FLATMAP_ROOT']
        self.__terminate_event = asyncio.Event()
        self.__process_lock = asyncio.Lock()
        self.__loop = uvloop.new_event_loop()
        self.start()

    async def full_log(self, pid):
    #=======================
        filename = log_file(pid)
        if os.path.exists(filename):
            with open(filename) as fp:
                return fp.read()
        return f'Missing log file... {filename}'

    async def get_log(self, id, start_line=1):
    #=========================================
        if id in self.__processes_by_id:
            process = self.__processes_by_id[id]
            log_lines = process.get_log(start_line)
            return log_lines
        return ''

    async def make(self, data: MakerData) -> MakerStatus:
    #====================================================
        params = {key: value for (key, value) in dataclasses.asdict(data).items()
                                if key in ['source', 'manifest', 'commit', 'force']}
        params.update({
            'output': self.__map_dir,
            'backgroundTiles': True,
            'silent': True,
            'noPathLayout': True,
            'logPath': settings['MAPMAKER_LOGS']  # Logfile name is `PROCESS_ID.json.log`
        })
        process = MakerProcess(params)
        async with self.__process_lock:
            self.__processes_by_id[process.id] = process
        if len(self.__running_processes):
            self.__queued_processes.put(process)
        else:
            await self.__start_process(process)
        return await self.status(process.id)

    def run(self):
    #=============
        self.__loop.run_until_complete(self._run())

    async def _run(self):
    #====================
        while not self.__terminate_event.is_set():
            still_running = []
            for id in self.__running_processes:
                async with self.__process_lock:
                    process = self.__processes_by_id[id]
                    while (msg := process.read_log_queue()) is not None:
                        pass
                    if process.is_alive():
                        still_running.append(id)
                    else:
                        process.close()
                        maker_result = process.result
                        if len(maker_result):
                            info = ', '.join([ f'{key}: {value}' for key in MAKER_RESULT_KEYS
                                            if (value := maker_result.get(key)) is not None ])
                            self.__log.info(f'Mapmaker succeeded: {process.name}, Map {info}')
                        else:
                            self.__log.error(f'Mapmaker FAILED: {process.name}')
                self.__running_processes = still_running
            if len(self.__running_processes) == 0:
                try:
                    process = self.__queued_processes.get(False)
                    await self.__start_process(process)
                except queue.Empty:
                    pass
            await asyncio.sleep(0.01)

    def terminate(self):
    #===================
        self.__terminate_event.set()

    async def status(self, id) -> MakerStatus:
    #=========================================
        pid = None
        if id in self.__processes_by_id:
            process = self.__processes_by_id[id]
            status = process.status
            pid = process.process_id
            if process.status in ['aborted', 'terminated']:
                async with self.__process_lock:
                    del self.__processes_by_id[id]
        else:
            status = 'unknown'
        return MakerStatus(id, status, pid)

    async def __start_process(self, process: MakerProcess):
    #======================================================
        process.start()
        async with self.__process_lock:
            self.__running_processes.append(process.id)
        self.__log.info(f'Started mapmaker process: {process.name}, PID: {process.process_id}')

#===============================================================================
#===============================================================================
