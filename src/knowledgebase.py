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
        database = Path(directory_path, KNOWLEDGE_BASE).resolve()
        if not database.exists():
            db = sqlite3.connect(database.as_posix())
            # create empty tables (schema...)
            db.close()
        self.__db = sqlite3.connect('{}?mode=ro'.format(database.as_uri()))

    def query(self, sql, *params):
        result = {}
        try:
            cursor = self.__db.cursor()
            rows = cursor.execute(sql, *params).fetchall()
            result['keys'] = tuple(d[0] for d in cursor.description)
            result['values'] = rows
        except (sqlite3.ProgrammingError, sqlite3.OperationalError) as error:
            result['error'] = str(error)
        return result

#===============================================================================
