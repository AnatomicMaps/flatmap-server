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
from pathlib import Path
from typing import Any

#===============================================================================

from landez.sources import MBTilesReader

#===============================================================================

from mapserver.maker import MAKER_SENTINEL
from mapserver.settings import settings
from mapserver.utils import json_metadata

#===============================================================================

def get_flatmap_list() -> list[dict]:
#====================================
    flatmap_list = []
    root_path = Path(settings['FLATMAP_ROOT']).resolve()
    if root_path.is_dir():
        for flatmap_dir in root_path.iterdir():
            index = Path(settings['FLATMAP_ROOT']) / flatmap_dir / 'index.json'
            mbtiles = Path(settings['FLATMAP_ROOT']) / flatmap_dir / 'index.mbtiles'
            map_making = Path(settings['FLATMAP_ROOT']) / flatmap_dir / MAKER_SENTINEL
            if (flatmap_dir.is_dir() and not map_making.exists()
            and index.exists() and mbtiles.exists()):
                with open(index) as fp:
                    index = json.loads(fp.read())
                version = index.get('version', 1.0)
                reader = MBTilesReader(mbtiles)
                if version >= 1.3:
                    metadata: dict[str, Any] = json_metadata(reader, 'metadata')
                    flatmap = {
                        'path': str(flatmap_dir)
                    }
                    if (('id' not in metadata or flatmap_dir.name != metadata['id'])
                     and ('uuid' not in metadata or flatmap_dir.name != metadata['uuid'].split(':')[-1])):
                        flatmap['error'] = f'Flatmap id mismatch with directory: {flatmap_dir}'
                        continue
                    flatmap.update({
                        'id': metadata['id'],
                        'name': metadata.get('name', metadata['id']),
                        'source': metadata['source'],
                        'version': version
                    })
                    if 'uuid' in metadata:
                        flatmap['uuid'] = metadata['uuid']
                    if 'style' in index:
                        flatmap['style'] = index['style']

                    ## add later...
                    ##id = flatmap.get('uuid', flatmap['id'])
                    ##flatmap['uri'] = f'{request.base_url}{FLATMAP_PATH_PREFIX}/{id}/'

                    if 'created' in metadata:
                        flatmap['created'] = metadata['created']
                        flatmap['creator'] = metadata['creator']
                    if 'git-status' in metadata:
                        flatmap['git-status'] = metadata['git-status']
                    if 'taxon' in metadata:
                        flatmap['taxon'] = metadata['taxon']
                        flatmap['describes'] = metadata['describes'] if 'describes' in metadata else flatmap['taxon']
                    elif 'describes' in metadata:
                        flatmap['taxon'] = metadata['describes']
                        flatmap['describes'] = flatmap['taxon']
                    if 'biological-sex' in metadata:
                        flatmap['biologicalSex'] = metadata['biological-sex']
                    if 'name' in metadata:
                        flatmap['name'] = metadata['name']
                    if 'connectivity' in metadata:
                        flatmap['sckan'] = metadata['connectivity']

                    flatmap_list.append(flatmap)
    return flatmap_list

#===============================================================================
#===============================================================================
