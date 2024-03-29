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

import hashlib
import logging
import multiprocessing
import multiprocessing.connection
import os
import sys
import threading
import urllib.error

#===============================================================================

from .settings import settings

from mapmaker.maker import MapMaker
from mapmaker.utils import log

#===============================================================================

# Base directory for logs (relative to ``MAPMAKER_ROOT``)

LOG_DIRECTORY = os.path.join(settings['MAPMAKER_ROOT'], 'log')

#===============================================================================

class MakerProcess(object):
    def __init__(self, map_id, process):
        self.__map_id = map_id
        self.__process = process
        self.__process_id = process.pid
        self.__sentinel = process.sentinel

    @property
    def exitcode(self):
        return self.__process.exitcode if self.__process is not None else -1

    @property
    def map_id(self):
        return self.__map_id

    @property
    def process_id(self):
        return self.__process_id

    @property
    def sentinel(self):
        return self.__sentinel

    def exists(self):
        return self.__process is not None

    def is_alive(self):
        return self.__process is not None and self.__process.is_alive()

    def terminate(self):
        self.__process = None

#===============================================================================

class Manager(threading.Thread):
    """A thread to manage flatmap generation"""
    def __init__(self):
        super().__init__(name='maker-thread')
        self.__map_dir = None
        self.__pids_by_sentinel = {}
        self.__processes_by_id = {}
        # Make sure we have a directory for log files
        settings['MAPMAKER_LOGS'] = os.path.join(settings['ROOT_PATH'], LOG_DIRECTORY)
        if not os.path.exists(settings['MAPMAKER_LOGS']):
            os.makedirs(settings['MAPMAKER_LOGS'])
        self.__logger = logging.getLogger('gunicorn.error')
        self.__map_dir = settings['FLATMAP_ROOT']
        self.start()

    def list(self):
    #==============
        pass

    def logfile(self, process_id):
    #=============================
        return os.path.join(settings['MAPMAKER_LOGS'],
                            '{}.log'.format(process_id))

    def make(self, map_source):
    #==========================
        map_id = hashlib.sha256(map_source.encode('utf8')).hexdigest()
        params = {
            'source': map_source,
            'id': map_id,
            'output': self.__map_dir,
            'backgroundTiles': True,
            'clean': True,
            'quiet': True,
            'logPath': settings['MAPMAKER_LOGS']  # Logfile name is `PROCESS_ID.log`
        }
        process = multiprocessing.Process(target=Manager._make_map, args=(params, ))
        process.start()
        maker_process = MakerProcess(map_id, process)
        self.__processes_by_id[process.pid] = maker_process
        self.__pids_by_sentinel[process.sentinel] = process.pid
        return maker_process

    def status(self, process_id):
    #============================
        if process_id in self.__processes_by_id:
            maker_process = self.__processes_by_id[process_id]
            if maker_process.is_alive():
                return 'running'
            elif maker_process.exists():
                return 'aborted'
            del self.__processes_by_id[process_id]
            try:
                del self.__pids_by_sentinel[maker_process.sentinel]
            except KeyError:
                pass
        return 'terminated'

    def run(self):
    #=============
        self.__logger.info('Manager running...')
        while True:
            sentinels = list(self.__pids_by_sentinel.keys())
            terminated = multiprocessing.connection.wait(sentinels, 0.1)
            for sentinel in terminated:
                process_id = self.__pids_by_sentinel.pop(sentinel)
                try:
                    process = self.__processes_by_id[process_id]
                    if process.exitcode != 0:
                        self.__processes_by_id[process_id].terminate()
                    else:
                        del self.__processes_by_id[process_id]
                except KeyError:
                    pass

    def terminate(self, process_id):
    #===============================
        pass

    @staticmethod
    def _make_map(params):
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
    process_id = generator.generate({'map': args.map})

