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

import logging
import multiprocessing
import multiprocessing.connection
import os
import queue
import sys
import threading
import uuid

#===============================================================================

from .settings import settings

from mapmaker import MapMaker
from mapmaker.utils import log

#===============================================================================

def log_file(pid):
    return os.path.join(settings['MAPMAKER_LOGS'], '{}.log'.format(pid))

#===============================================================================

class MakerProcess(multiprocessing.Process):
    def __init__(self, params: dict):
        id = str(uuid.uuid4())
        super().__init__(target=Manager.make_map, args=(params, ), name=f'Process-{id}')
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
        super().close()

    def start(self):
    #===============
        log.info('Starting process:', self.name)
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
        self.__ids_by_sentinel: dict[int, str] = {}
        self.__processes_by_id: dict[str, MakerProcess] = {}
        self.__queued_processes:queue.Queue[MakerProcess] = queue.Queue()

        # Make sure we have a directory for log files
        # Base directory for logs (relative to ``MAPMAKER_ROOT``)
        settings['MAPMAKER_LOGS'] = os.path.join(settings['ROOT_PATH'],
                                                 os.path.join(settings['MAPMAKER_ROOT'],
                                                 'log'))
        if not os.path.exists(settings['MAPMAKER_LOGS']):
            os.makedirs(settings['MAPMAKER_LOGS'])
        self.__logger = logging.getLogger('gunicorn.error')
        self.__map_dir = settings['FLATMAP_ROOT']
        self.start()

    def list(self):
    #==============
        pass

    def full_log(self, pid):
    #=======================
        filename = log_file(pid)
        if os.path.exists(filename):
            with open(filename) as fp:
                return fp.read()
        return f'Missing log file... {filename}'

    def get_log(self, id, start_line=1):
    #===================================
        if id in self.__processes_by_id:
            process = self.__processes_by_id[id]
            if (filename := process.log_file) is not None and os.path.exists(filename):
                with open(filename) as fp:
                    return '\n'.join(fp.read().split('\n')[start_line-1:])
        return ''

    def make(self, params) -> dict:
    #==============================
        params = {key: value for (key, value) in params.items()
                                if key in ['source', 'manifest', 'commit']}
        params.update({
            'output': self.__map_dir,
            'backgroundTiles': True,
            'clean': True,  ## remove and don't make if map exists (log.error() and exit(1))
            'quiet': True,  ## what does this do? Isn't it now the default??
            ##  logFile based on process number, but only number initialised to last log file...
            'logPath': settings['MAPMAKER_LOGS']  # Logfile name is `PROCESS_ID.log`
        })
        process = MakerProcess(params)
        log.info('Created process:', process.name)
        self.__processes_by_id[process.id] = process
        if len(self.__ids_by_sentinel):
            self.__queued_processes.put(process)
        else:
            self.__start_process(process)
        return self.status(process.id)

    def run(self):
    #=============
        self.__logger.info('Manager running...')
        while True:
            sentinels = list(self.__ids_by_sentinel.keys())
            terminated = multiprocessing.connection.wait(sentinels, 0.1)
            for sentinel in terminated:
                if isinstance(sentinel, int):
                    id = self.__ids_by_sentinel[sentinel]
                    try:
                        process = self.__processes_by_id[id]
                        if not process.is_alive():
                            process.close()
                            del self.__ids_by_sentinel[sentinel]
                    except KeyError:
                        pass
            if len(self.__ids_by_sentinel) == 0:
                try:
                    process = self.__queued_processes.get(False)
                    self.__start_process(process)
                except queue.Empty:
                    pass

    def status(self, id) -> dict:
    #============================
        result = {
            'process': id
        }
        if id in self.__processes_by_id:
            process = self.__processes_by_id[id]
            result['status'] = process.status
            if (pid := process.process_id) is not None:
                result['pid'] = pid
            if process.status in ['aborted', 'terminated']:
                del self.__processes_by_id[id]
        else:
            result['status'] = 'unknown'
        return result

    def __start_process(self, process: MakerProcess):
    #================================================
        process.start()
        self.__ids_by_sentinel[process.sentinel] = process.id

    @staticmethod
    def make_map(params):
    #=====================
        try:
            mapmaker = MapMaker(params)
            mapmaker.make()
        except Exception as err:
            log.error(str(err))
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

