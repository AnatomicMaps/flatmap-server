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

import gzip
import io
import json
import pathlib
import sqlite3
from typing import Any

#===============================================================================

from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

from litestar import exceptions, get, MediaType, Request, Response, Router
from litestar.response import File

from PIL import Image

#===============================================================================

from ..knowledge.hierarchy import AnatomicalHierarchy
from ..settings import settings
from ..utils import get_metadata, json_metadata, json_map_metadata

#===============================================================================
"""
If a file with this name exists in the map's output directory then the map
is in the process of being made
"""
MAKER_SENTINEL = '.map_making'

"""
The name of the log file from when the map was made
"""
MAKER_LOG = 'mapmaker.log.json'
OLD_MAKER_LOG = 'mapmaker.log'

#===============================================================================

FLATMAP_PATH_PREFIX = 'flatmap'

#===============================================================================

# Build and cache a hierarchy of anataomical terms used by a flatmap

anatomical_hierarchy = AnatomicalHierarchy()

#===============================================================================
#===============================================================================

PATHWAYS_CACHE = 'pathways.json'

def pathways(map_uuid: str) -> dict[str, Any]:
#=============================================
    pathways_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / PATHWAYS_CACHE
    try:
        with open(pathways_file) as fp:
            return json.load(fp)
    except Exception:
        pass
    pathways = json_map_metadata(map_uuid, 'pathways')
    with open(pathways_file, 'w') as fp:
        json.dump(pathways, fp)
    return pathways

#===============================================================================
#===============================================================================

def blank_tile():
    tile = Image.new('RGBA', (1, 1), color=(255, 255, 255, 0))
    file = io.BytesIO()
    tile.save(file, 'png')
    return file.getvalue()

#===============================================================================
#===============================================================================

@get('/')
async def flatmap_maps(request: Request) -> list:
    """
    Get a list of available flatmaps.

    :>jsonarr string id: the flatmap's unique identifier on the server
    :>jsonarr string source: the map's source URL
    :>jsonarr string created: when the map was generated
    :>jsonarr string describes: the map's description
    """
    flatmap_list = []
    root_path = pathlib.Path(settings['FLATMAP_ROOT'])
    if root_path.is_dir():
        for flatmap_dir in root_path.iterdir():
            index = pathlib.Path(settings['FLATMAP_ROOT']) / flatmap_dir / 'index.json'
            mbtiles = pathlib.Path(settings['FLATMAP_ROOT']) / flatmap_dir / 'index.mbtiles'
            map_making = pathlib.Path(settings['FLATMAP_ROOT']) / flatmap_dir / MAKER_SENTINEL
            if (flatmap_dir.is_dir() and not map_making.exists()
            and index.exists() and mbtiles.exists()):
                with open(index) as fp:
                    index = json.loads(fp.read())
                version = index.get('version', 1.0)
                reader = MBTilesReader(mbtiles)
                if version >= 1.3:
                    metadata: dict[str, Any] = json_metadata(reader, 'metadata')
                    if (('id' not in metadata or flatmap_dir.name != metadata['id'])
                     and ('uuid' not in metadata or flatmap_dir.name != metadata['uuid'].split(':')[-1])):
                        request.logger.error(f'Flatmap id mismatch: {flatmap_dir}')
                        continue
                    flatmap = {
                        'id': metadata['id'],
                        'source': metadata['source'],
                        'version': version
                    }
                    if 'uuid' in metadata:
                        flatmap['uuid'] = metadata['uuid']
                        id = metadata['uuid']
                    else:
                        id = metadata['id']
                    flatmap['uri'] = f'{request.base_url}{FLATMAP_PATH_PREFIX}/{id}/'
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
                else:
                    source_row = None
                    try:
                        source_row = get_metadata(reader, 'source')
                    except (InvalidFormatError, sqlite3.OperationalError):
                        raise exceptions.NotFoundException(detail=f'Cannot read tile database: {mbtiles}')
                    if source_row is None:
                        continue
                    flatmap = {
                        'id': flatmap_dir.name,
                        'source': source_row[0]
                    }
                    created = get_metadata(reader, 'created')
                    if created is not None:
                        flatmap['created'] = created[0]
                    describes = get_metadata(reader, 'describes')
                    if describes is not None and describes[0]:
                        flatmap['describes'] = describes[0]
                flatmap_list.append(flatmap)
    return flatmap_list

#===============================================================================

@get('flatmap/{map_uuid:str}/')
async def flatmap_index(request: Request, map_uuid: str) -> dict|Response:
    """
    Return a representation of a flatmap.

    :param map_uuid: The flatmap identifier
    :type map_uuid: string

    :reqheader Accept: Determines the response content

    If an SVG representation of the map exists and the :mailheader:`Accept` header
    doesn't specify a JSON response then the SVG is returned, otherwise the
    flatmap's ``index.json`` is returned.
    """
    index_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'index.json'
    if not index_file.exists():
        return Response(content={'detail': 'Missing map index'}, status_code=404)
    with open(index_file) as fp:
        index = json.load(fp)
    if 'json' not in request.headers.get('accept', '*/*'):
        svg_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / f'{index["id"]}.svg'
        if not svg_file.exists():
            svg_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'images' / f'{index["id"]}.svg'
        if svg_file.exists():
            with open(svg_file) as fp:
                return Response(content=fp.read(), media_type='image/svg+xml')
    return index

#===============================================================================

@get('flatmap/{map_uuid:str}/log')
async def flatmap_maker_log(map_uuid: str) -> File:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / MAKER_LOG
    if not path.exists():
        path = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / OLD_MAKER_LOG
        if not path.exists():
            raise exceptions.NotFoundException(detail=f'Missing {MAKER_LOG}')
        return File(path=path, filename=OLD_MAKER_LOG, media_type=MediaType.TEXT)
    return File(path=path, filename=MAKER_LOG, media_type=MediaType.JSON)

#===============================================================================

@get('flatmap/{map_uuid:str}/style')
async def flatmap_style(map_uuid: str) -> File:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'style.json'
    return File(path=path, media_type=MediaType.JSON)

#===============================================================================

## DEPRECATED
@get('flatmap/{map_uuid:str}/markers', include_in_schema=False)
async def flatmap_markers(map_uuid: str) -> File:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'markers.json'
    return File(path=path, media_type=MediaType.JSON)

#===============================================================================

@get('flatmap/{map_uuid:str}/layers')
async def flatmap_layers(map_uuid: str) -> dict:
    try:
        return json_map_metadata(map_uuid, 'layers')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_uuid:str}/metadata')
async def flatmap_metadata(map_uuid: str) -> dict:
    try:
        return json_map_metadata(map_uuid, 'metadata')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================
#===============================================================================

@get('flatmap/{map_uuid:str}/pathways')
async def flatmap_pathways(map_uuid: str) -> dict:
    try:
        return pathways(map_uuid)
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_uuid:str}/connectivity/{path_id:path}')
async def flatmap_connectivity(map_uuid: str, path_id: str) -> dict:
    path_id = path_id[1:]       # Remove leading '/''
    try:
        path_data = pathways(map_uuid)
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))
    paths = path_data.get('paths', {})
    if not path_id.startswith('ilxtr:') or path_id not in paths:
        raise exceptions.NotFoundException(detail=f'Unknown path: {path_id}')
    path = paths[path_id]
    return {
        'path': path_id,
        'connectivity': path.get('connectivity', []),
        'axons': path.get('axons', []),
        'dendrites': path.get('dendrites', []),
        'somas': path.get('somas', [])
    }

#===============================================================================
#===============================================================================

@get('flatmap/{map_uuid:str}/images/{image:str}')
async def flatmap_image(map_uuid: str, image:str) -> Response:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'images' / image
    if not path.exists():
        raise exceptions.NotFoundException(detail=f'Missing image: {image}')
    return File(path=path, filename=image, content_disposition_type='inline')

#===============================================================================

@get('flatmap/{map_uuid:str}/mvtiles/{z:int}/{x:int}/{y:int}')
async def flatmap_vector_tiles(map_uuid: str, z: int, y:int, x: int) -> Response:
    try:
        mbtiles = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / 'index.mbtiles'
        tile_reader = MBTilesReader(mbtiles)
        tile_bytes = tile_reader.tile(z, x, y)
        if get_metadata(tile_reader, 'compressed'):
            tile_bytes = gzip.decompress(tile_bytes)
        return Response(content=tile_bytes, media_type='application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        raise exceptions.NotFoundException(detail='Cannot read tile database')
    return Response(content='', status_code=204)

#===============================================================================

@get('flatmap/{map_uuid:str}/tiles/{layer:str}/{z:int}/{x:int}/{y:int}')
async def flatmap_image_tiles(map_uuid: str, layer: str, z: int, y:int, x: int) -> Response:
    try:
        mbtiles = pathlib.Path(settings['FLATMAP_ROOT']) / map_uuid / f'{layer}.mbtiles'
        reader = MBTilesReader(mbtiles)
        return Response(content=reader.tile(z, x, y), media_type='image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        raise exceptions.NotFoundException(detail='Cannot read tile database')
    return Response(content=blank_tile(), media_type='image/png')

#===============================================================================

@get('flatmap/{map_uuid:str}/annotations')
async def flatmap_annotation(map_uuid: str) -> dict:
    try:
        return json_map_metadata(map_uuid, 'annotations')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_uuid:str}/termgraph')
async def flatmap_termgraph(map_uuid: str) -> dict:
    try:
        return anatomical_hierarchy.get_hierachy(map_uuid)
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================
#===============================================================================

flatmap_router = Router(
    path="/",
    route_handlers=[
        flatmap_annotation,
        flatmap_image,
        flatmap_image_tiles,
        flatmap_index,
        flatmap_layers,
        flatmap_maker_log,
        flatmap_maps,
        flatmap_markers,    ## DEPRECATED
        flatmap_metadata,
        flatmap_pathways,
        flatmap_connectivity,
        flatmap_style,
        flatmap_termgraph,
        flatmap_vector_tiles
    ]
)

#===============================================================================
#===============================================================================
