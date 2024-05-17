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

import asyncio
import multiprocessing
import multiprocessing.connection
import os
import queue
import sys
import threading
from time import sleep
import uuid

import uvloop

#===============================================================================

from .settings import settings

from mapmaker import MapMaker
import mapmaker.utils as utils

#===============================================================================

def log_file(pid):
    return os.path.join(settings['MAPMAKER_LOGS'], '{}.log'.format(pid))

#===============================================================================

def _run_in_loop(func, args):
    loop = uvloop.new_event_loop()
    loop.run_until_complete(func(args))

#===============================================================================

class MakerProcess(multiprocessing.Process):
    def __init__(self, params: dict):
        id = str(uuid.uuid4())
        super().__init__(target=_run_in_loop, args=(Manager.make_map, params), name=f'Process-{id}')
        self.__id = id
        self.__process_id = None
        self.__log_file = None
        self.__status = 'queued'

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
    def status(self) -> str:
        return self.__status
    @status.setter
    def status(self, value: str):
        self.__status = value

    def close(self):
    #===============
        self.__status = 'terminated' if self.exitcode == 0 else 'aborted'
        super().join()
        super().close()

    def start(self):
    #===============
        utils.log.info('Starting process:', self.name)
        self.__status = 'running'
        super().start()
        self.__process_id = self.pid
        self.__log_file = log_file(self.pid)

#===============================================================================

class Manager(threading.Thread):
    """A thread to manage flatmap generation"""
    def __init__(self):
        super().__init__(name='maker-thread')
        self.__map_dir = None
        self.__processes_by_id: dict[str, MakerProcess] = {}
        self.__running_processes: list[str] = []
        self.__queued_processes:queue.Queue[MakerProcess] = queue.Queue()

        # Make sure we have a directory for log files
        # Base directory for logs (relative to ``MAPMAKER_ROOT``)
        settings['MAPMAKER_LOGS'] = os.path.join(settings['ROOT_PATH'],
                                                 os.path.join(settings['MAPMAKER_ROOT'],
                                                 'log'))
        if not os.path.exists(settings['MAPMAKER_LOGS']):
            os.makedirs(settings['MAPMAKER_LOGS'])
        self.__map_dir = settings['FLATMAP_ROOT']
        self.__terminate_event = asyncio.Event()
        self.__process_lock = threading.Lock()
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
            if (filename := process.log_file) is not None and os.path.exists(filename):
                with open(filename) as fp:
                    return '\n'.join(fp.read().split('\n')[start_line-1:])
        return ''

    async def make(self, params) -> dict:
    #====================================
        params = {key: value for (key, value) in params.items()
                                if key in ['source', 'manifest', 'commit', 'force']}
        params.update({
            'output': self.__map_dir,
            'backgroundTiles': True,
            'clean': True,  ## remove and don't make if map exists (log.error() and exit(1))
            'quiet': True,  ## what does this do? Isn't it now the default??
            'logPath': settings['MAPMAKER_LOGS']  # Logfile name is `PROCESS_ID.log`
        })
        process = MakerProcess(params)
        utils.log.info('Created process:', process.name)
        with self.__process_lock:
            self.__processes_by_id[process.id] = process
        if len(self.__running_processes):
            self.__queued_processes.put(process)
        else:
            self.__start_process(process)
        return await self.status(process.id)

    def run(self):
    #=============
        while not self.__terminate_event.is_set():
            still_running = []
            for id in self.__running_processes:
                with self.__process_lock:
                    process = self.__processes_by_id[id]
                    if process.is_alive():
                        still_running.append(id)
                    else:
                        process.close()
                self.__running_processes = still_running
            if len(self.__running_processes) == 0:
                try:
                    process = self.__queued_processes.get(False)
                    self.__start_process(process)
                except queue.Empty:
                    pass
            sleep(0.01)

    def terminate(self):
    #===================
        self.__terminate_event.set()

    async def status(self, id) -> dict:
    #==================================
        result = {
            'process': id
        }
        if id in self.__processes_by_id:
            process = self.__processes_by_id[id]
            result['status'] = process.status
            if (pid := process.process_id) is not None:
                result['pid'] = pid
            if process.status in ['aborted', 'terminated']:
                with self.__process_lock:
                    del self.__processes_by_id[id]
        else:
            result['status'] = 'unknown'
        return result

    def __start_process(self, process: MakerProcess):
    #================================================
        process.start()
        with self.__process_lock:
            self.__running_processes.append(process.id)

    @staticmethod
    def make_map(params):
    #=====================
        try:
            mapmaker = MapMaker(params)
            mapmaker.make()
        except Exception as err:
            utils.log.exception(err, exc_info=True)
            sys.exit(1)

#===============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser('Generate a flatmap in the background')
    parser.add_argument('map', metavar="MAP",
        help='URL or directory path containing a flatmap manifest')

    args = parser.parse_args()

    generator = Manager()
    status = generator.make_map({'map': args.map})

