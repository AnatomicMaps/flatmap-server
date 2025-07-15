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
import os
import queue
import threading

#===============================================================================

import uvloop

#===============================================================================

from mapknowledge import NERVE_TYPE
from mapknowledge.competency import clean_knowledge_source
from mapknowledge.competency import KnowledgeList, KnowledgeSource

#===============================================================================

from ..settings import settings
from ..utils import json_map_metadata

from .knowledge import CompetencyKnowledge

#===============================================================================

def map_knowledge(map_uuid: str, competency_db: CompetencyKnowledge) -> KnowledgeList:
#=====================================================================================
    metadata = json_map_metadata(map_uuid, 'metadata')
    if map_uuid != metadata.get('uuid'):
        raise IOError("Flatmap source UUID doesn't match the provided UUID.")

    sckan_release = metadata.get('connectivity', {}).get('npo', {}).get('release', '')
    map_knowledge_source = clean_knowledge_source(sckan_release)

    annotations = json_map_metadata(map_uuid, 'annotations')
    annotated_features = { models: feature
                            for feature in annotations.values()
                                if (models := feature.get('models')) is not None }

    descriptions = competency_db.term_descriptions(map_knowledge_source)
    path_properties = competency_db.path_properties(map_knowledge_source)
    path_evidence = competency_db.path_evidence(map_knowledge_source)
    path_phenotypes = competency_db.path_phenotypes(map_knowledge_source)

    # Collect all map knowledge
    knowledge_terms = {}

    # Path features (i.e. those with connectivity)
    pathways = json_map_metadata(map_uuid, 'pathways').get('paths', {})
    nerve_terms = set()
    for path_id, path_knowledge in pathways.items():
        if 'connectivity' not in path_knowledge:
            continue
        annotations = annotated_features.get(path_id, {})
        properties = path_properties.get(path_id, {})
        knowledge_terms[path_id] = {
            'id': path_id,
            'source': map_uuid,
            'label': annotations['label'],
            'long-label': descriptions.get(path_id, annotations['label']),
            'connectivity': path_knowledge['connectivity'],
            'taxons': annotations.get('taxons', []),
            'forward-connections': path_knowledge.get('forward-connections', []),
            'node-phenotypes': path_knowledge.get('node-phenotypes', {}),
            'nerves': path_knowledge.get('node-nerves', []),
            'phenotypes': path_phenotypes.get(path_id, []),
            'references': path_evidence.get(path_id, []),
        }
        if 'alert' in properties:
            knowledge_terms[path_id]['alert'] = properties['alert']
        if 'biologicalSex' in properties:
            knowledge_terms[path_id]['biologicalSex'] = properties['biologicalSex']
        if 'pathDisconnected' in properties:
            knowledge_terms[path_id]['pathDisconnected'] = properties['pathDisconnected']
        nerve_terms.update(term for node in knowledge_terms[path_id]['nerves'] for term in [node[0]] + node[1])

    # Non-path features with an anatomical term
    for feature_id, properties in annotated_features.items():
        if feature_id not in knowledge_terms:
            knowledge_terms[feature_id] = {
                'id': feature_id,
                'source': map_uuid,
                'label': properties['label'],
                'long-label': descriptions.get(feature_id, properties['label']),
            }
            if properties.get('type') == 'nerve' or feature_id in nerve_terms:
                knowledge_terms[feature_id]['type'] = NERVE_TYPE

    return KnowledgeList(KnowledgeSource(map_uuid, sckan_release, metadata['name']), list(knowledge_terms.values()))

#===============================================================================

'''
class Manager(threading.Thread):
    """A thread to update the CQ database with published flatmap knowledge"""
    def __init__(self):
        super().__init__(name='CQ-thread')
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
                    if process.is_alive():
                        still_running.append(id)
                    else:
                        process.close()
                        maker_result = process.result
                        status = 'Finished' if process.status == 'terminated' else 'FAILED'
                        info = ', '.join([ f'{key}: {value}' for key in MAKER_RESULT_KEYS
                                            if (value := maker_result.get(key)) is not None ])
                        self.__log.info(f'{status} mapmaker process: {process.name}, Map {info}')
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

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser('Generate a flatmap in the background')
    parser.add_argument('map', metavar="MAP",
        help='URL or directory path containing a flatmap manifest')

    args = parser.parse_args()

    generator = Manager()
    status = generator.make({'source': args.map})

#===============================================================================
#===============================================================================
'''
