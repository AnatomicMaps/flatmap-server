#===============================================================================
#
#  Flatmap server tools
#
#  Copyright (c) 2024 David Brooks
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

class CleanKnowledgeStore:
    def __init__(self, flatmap_dir: str):
        self.__flatmap_dir = Path(flatmap_dir)
        self.__db = sqlite3.connect(self.__flatmap_dir / 'knowledgebase.db')

    def close(self):
        self.__db.close()

    def purge(self, table: str, flatmap_col: str):
        rowids = []
        for row in self.__db.execute(f'SELECT rowid, {flatmap_col} from {table}').fetchall():
            if row[1] is None or row[1].strip() == '' or not (self.__flatmap_dir / row[1]).exists():
                rowids.append(row[0])
        if len(rowids):
            self.__db.execute(f'DELETE from {table} where rowid in {tuple(rowids)}')
            self.__db.commit()

#===============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Purge unknown flatmaps from Knowledge Store')
    parser.add_argument('flatmap_base', metavar='FLATMAP_BASE', help='Directory containing Knowledge Store')
    args = parser.parse_args()

    cleaner = CleanKnowledgeStore(args.flatmap_base)
    cleaner.purge('flatmaps', 'id')
    cleaner.purge('flatmap_entities', 'flatmap')
    cleaner.close()

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
