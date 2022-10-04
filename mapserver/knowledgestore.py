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

import sqlite3

#===============================================================================

import flatmapknowledge

#===============================================================================

class KnowledgeStore(flatmapknowledge.KnowledgeStore):
    def __init__(self, directory_path, create=False, read_only=True):
        try:
            super().__init__(directory_path, create=create, read_only=read_only)
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
            cursor = self.db.execute(sql, params)
            result = {
                'keys': tuple(d[0] for d in cursor.description),
                'values': cursor.fetchall()
            }
            cursor.close()
            return result
        except (sqlite3.DatabaseError, sqlite3.ProgrammingError, sqlite3.OperationalError) as error:
            return { 'error': str(error) }

#===============================================================================
