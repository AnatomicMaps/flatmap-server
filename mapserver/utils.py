#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-2024  David Brooks
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

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Optional

#===============================================================================

from landez.sources import MBTilesReader, InvalidFormatError

#===============================================================================

from .settings import settings

#===============================================================================

def get_metadata(reader: MBTilesReader, name: str) -> Optional[str]:
#===================================================================
    if (cursor:=reader._query('SELECT value FROM metadata WHERE name=?', (name, ))) is not None:
        return cursor.fetchone()

def json_metadata(tile_reader: MBTilesReader, name: str) -> dict[str, Any]:
#==========================================================================
    row = None
    try:
        if (cursor:=tile_reader._query('SELECT value FROM metadata WHERE name=?', (name,))) is not None:
            row = cursor.fetchone()
    except (InvalidFormatError, sqlite3.OperationalError):
        raise IOError('Cannot read tile database')
    return {} if row is None else json.loads(row[0])

def json_map_metadata(map_id: str, name: str) -> dict[str, Any]:
#===============================================================
    map_path = Path(settings['FLATMAP_ROOT']) / map_id
    index = map_path / 'index.json'
    with open(index) as fp:
        version = float(json.load(fp).get('version', 1.6))
    if version < 2.0:
        mbtiles = map_path / 'index.mbtiles'
        if mbtiles.exists():
            return json_metadata(MBTilesReader(mbtiles), name)
    else:
        annotation_file = map_path / 'annotations.json'
        if annotation_file.exists():
            with open(annotation_file) as fp:
                annotation = json.load(fp)
            return annotation.get(name, {})
    return {}

#===============================================================================
#===============================================================================
