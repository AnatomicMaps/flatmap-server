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

from pathlib import Path

import sqlite3

#===============================================================================

KNOWLEDGE_BASE = 'knowledgebase.db'

#===============================================================================

class KnowledgeBase(object):
    def __init__(self, directory_path):
        self.__database = Path(directory_path, KNOWLEDGE_BASE).resolve()
        try:
            if not self.__database.exists():
                db = sqlite3.connect(self.__database)
                db.close()
            self.__db = sqlite3.connect('{}?mode=ro'.format(self.__database.as_uri()), uri=True)
            self.__error = None
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as error:
            self.__db = None
            self.__error = str(error)

    @property
    def database(self):
        return self.__database

    @property
    def error(self):
        return self.__error

    def query(self, sql, *params):
        if self.__db is None:
            return { 'error': self.__error }
        try:
            cursor = self.__db.cursor()
            rows = cursor.execute(sql, *params).fetchall()
            return {
                'keys': tuple(d[0] for d in cursor.description),
                'values': rows
            }
        except (sqlite3.DatabaseError, sqlite3.ProgrammingError, sqlite3.OperationalError) as error:
            return { 'error': str(error) }

#===============================================================================
