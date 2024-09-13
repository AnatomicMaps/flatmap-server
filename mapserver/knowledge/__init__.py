#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-21  David Brooks
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

import os
import json
import sqlite3
import sys

#===============================================================================

import flatmapknowledge
from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

#===============================================================================

from ..settings import settings

#===============================================================================

def read_metadata(tile_reader: MBTilesReader, name: str):
    row = None
    try:
        if (query_result:=tile_reader._query("SELECT value FROM metadata WHERE name='{}'".format(name))) is not None:
            row = query_result.fetchone()
    except (InvalidFormatError, sqlite3.OperationalError):
        raise IOError('Cannot read tile database')
    return {} if row is None else json.loads(row[0])

def get_metadata(map_id: str, name: str):
    mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
    return read_metadata(MBTilesReader(mbtiles), name)

#===============================================================================

class KnowledgeStore(flatmapknowledge.KnowledgeStore):
    def __init__(self, directory_path, create=False):
        try:
            super().__init__(directory_path, create=create, read_only=True, verbose=False)
            self.__error = None
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as error:
            self.__error = str(error)

    @property
    def error(self):
        return self.__error

    def query(self, sql, params):
        if self.__error is not None:
            return { 'error': self.__error }
        try:
            cursor = self.db.execute(sql, params)  # type: ignore
            result = {
                'keys': tuple(d[0] for d in cursor.description),
                'values': cursor.fetchall()
            }
            cursor.close()
            return result
        except (sqlite3.DatabaseError, sqlite3.ProgrammingError, sqlite3.OperationalError) as error:
            return { 'error': str(error) }

#===============================================================================
