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

import multiprocessing

#===============================================================================

from mapmaker.maker import Flatmap

#===============================================================================

class Manager(object):
    """Manage flatmap generation"""
    def __init__(self):
        self.__processes = {}

    # run a thread selecting on a list of process.sentinel (with sy 100ms t/o)
    # to remove terminated processes from self.__processes

    def generate(self, options):
    #===========================
        process = multiprocessing.Process(target=Manager.make_flatmap, args=(options,))
        process.start()
        self.__processes[process.pid]= process
        return process.pid

    @staticmethod
    def make_flatmap(options):
    #=========================
        try:
            flatmap = Flatmap(options)
            flatmap.make()
        except:
            pass
            # sys.pid() ??
            # get exception message and update process status...
            # use connection? pipe??

    def status(self, process_id):
    #============================
        if process_id not in self.__processes:
            return 'terminated'
        elif self.__processes[process_id].is_alive():
            return 'running'
        else:
            del self.__processes[process_id]
            return 'terminated'

#===============================================================================
