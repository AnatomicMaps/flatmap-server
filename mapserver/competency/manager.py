#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-25  David Brooks
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
import threading

#===============================================================================

import uvloop

#===============================================================================

from ..server.utils import get_flatmap_list
from ..settings import settings

#===============================================================================

from . import COMPETENCY_DATABASE, COMPETENCY_USER, COMPETENCY_HOST
from .flatmap import anatomical_map_knowledge, ignore_map
from .knowledge import CompetencyKnowledge

#===============================================================================

CHECK_MAPS_INTERVAL = 300   # 5 minutes between checking for any updated flatmaps
LOAD_MAP_INTERVAL   =   5   # 5 seconds between loading individual maps

#===============================================================================

competency_manager = None

#===============================================================================

class ComptencyManager(threading.Thread):
    """A thread to update the CQ database with published flatmap knowledge"""
    def __init__(self):
        super().__init__(name='CQ-thread')
        self.__log = settings['LOGGER']
        self.__terminate_event = asyncio.Event()
        self.__loop = uvloop.new_event_loop()
        self.start()

    def run(self):
    #=============
        self.__loop.run_until_complete(self._run())

    async def _run(self):
    #====================
        while not self.__terminate_event.is_set():
            await self.__check_maps()
            await asyncio.sleep(CHECK_MAPS_INTERVAL)

    def terminate(self):
    #===================
        self.__terminate_event.set()

    async def __check_maps(self):
    #=============================
        db = CompetencyKnowledge(COMPETENCY_USER, COMPETENCY_HOST, COMPETENCY_DATABASE)
        for flatmap in get_flatmap_list():
            if self.__terminate_event.is_set():
                return
            elif (uuid := flatmap.get('uuid')) is not None:
                ## need to check map's creation date with source timestamp in CQ database
                ## and load if map is more recent...
                if not db.has_knowledge_source(uuid):
                    self.__load_map(db, uuid)
                    await asyncio.sleep(LOAD_MAP_INTERVAL)

    def __load_map(self, db: CompetencyKnowledge, uuid: str):
    #========================================================
        knowledge = anatomical_map_knowledge(uuid, db)
        if knowledge is not None:
            try:
                db.import_knowledge(knowledge)
                self.__log.info(f'Loaded knowledge for map {uuid} into CQ database')
            except Exception as error:
                ignore_map(uuid, str(error), settings['LOGGER'].error)

#===============================================================================

def initialise_competency_update():
#==================================
    global competency_manager
    competency_manager = ComptencyManager()

def terminate_competency_update():
#=================================
    global competency_manager
    if competency_manager is not None:
        competency_manager.terminate()
        competency_manager = None

#===============================================================================
#===============================================================================
