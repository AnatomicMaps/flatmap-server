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

#===============================================================================

from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

from litestar import exceptions, get, Request, Response, Router
from litestar.response import File

from PIL import Image

#===============================================================================

from ..knowledge.hierarchy import AnatomicalHierarchy
from ..settings import settings
from ..utils import get_metadata, json_metadata, json_map_metadata, read_json

#===============================================================================
"""
If a file with this name exists in the map's output directory then the map
is in the process of being made
"""
MAKER_SENTINEL = '.map_making'

#===============================================================================

FLATMAP_PATH_PREFIX = 'flatmap'

#===============================================================================

# Build and cache a hierarchy of anataomical terms used by a flatmap

anatomical_hierarchy = AnatomicalHierarchy()

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
async def maps(request: Request) -> list:
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
                    metadata: dict[str, str] = json_metadata(reader, 'metadata')
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

@get('flatmap/{map_id:str}/')
async def map_index(request: Request, map_id: str) -> Response:
    """
    Return a representation of a flatmap.

    :param map_id: The flatmap identifier
    :type map_id: string

    :reqheader Accept: Determines the response content

    If an SVG representation of the map exists and the :mailheader:`Accept` header
    doesn't specify a JSON response then the SVG is returned, otherwise the
    flatmap's ``index.json`` is returned.
    """
    index_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'index.json'
    if not index_file.exists():
        return Response(content={'detail': 'Missing map index'}, status_code=404)
    with open(index_file) as fp:
        index = json.load(fp)
    if request.accept.accepts('image/svg+xml'):
        svg_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / f'{index["id"]}.svg'
        if not svg_file.exists():
            svg_file = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'images' / f'{index["id"]}.svg'
        if not svg_file.exists():
            with open(svg_file) as fp:
                return Response(content=fp.read(), media_type='image/svg+xml')
    return index

#===============================================================================

@get('flatmap/{map_id:str}/log', media_type='text/plain')
async def mapmaker_log(map_id: str) -> File:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'mapmaker.log'
    if not path.exists():
        raise exceptions.NotFoundException(detail='Missing mapmaker.log')
    return File(path=path, filename='mapmaker.log')

#===============================================================================

@get('flatmap/{map_id:str}/style')
async def map_style(map_id: str) -> dict|list:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'style.json'
    return read_json(path)

#===============================================================================

## DEPRECATED
@get('flatmap/{map_id:str}/markers')
async def map_markers(map_id: str) -> dict|list:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'markers.json'
    return read_json(path)

#===============================================================================

@get('flatmap/{map_id:str}/layers')
async def map_layers(map_id: str) -> dict:
    try:
        return json_map_metadata(map_id, 'layers')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_id:str}/metadata')
async def map_metadata(map_id: str) -> dict:
    try:
        return json_map_metadata(map_id, 'metadata')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_id:str}/pathways')
async def map_pathways(map_id: str) -> dict:
    try:
        return json_map_metadata(map_id, 'pathways')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_id:str}/images/{image:str}')
async def map_background(map_id: str, image:str) -> Response:
    path = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'images' / image
    if not path.exists():
        raise exceptions.NotFoundException(detail=f'Missing image: {image}')
    return File(path=path, filename=image)

#===============================================================================

@get('flatmap/{map_id:str}/mvtiles/{z:int}/{x:int}/{y:int}')
async def vector_tiles(map_id: str, z: int, y:int, x: int) -> Response:
    try:
        mbtiles = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / 'index.mbtiles'
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

@get('flatmap/{map_id:str}/tiles/{layer:int}/{z:int}/{x:int}/{y:int}')
async def image_tiles(map_id: str, layer: str, z: int, y:int, x: int) -> Response:
    try:
        mbtiles = pathlib.Path(settings['FLATMAP_ROOT']) / map_id / f'{layer}.mbtiles'
        reader = MBTilesReader(mbtiles)
        return Response(content=reader.tile(z, x, y), media_type='image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        raise exceptions.NotFoundException(detail='Cannot read tile database')
    return Response(content=blank_tile(), media_type='image/png')

#===============================================================================

@get('flatmap/{map_id:str}/annotations')
async def map_annotation(map_id: str) -> dict:
    try:
        return json_map_metadata(map_id, 'annotations')
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================

@get('flatmap/{map_id:str}/termgraph')
async def map_termgraph(map_id: str) -> dict:
    try:
        return anatomical_hierarchy.get_hierachy(map_id)
    except IOError as err:
        raise exceptions.NotFoundException(detail=str(err))

#===============================================================================
#===============================================================================

flatmap_router = Router(
    path="/",
    route_handlers=[
        image_tiles,
        mapmaker_log,
        maps,
        map_annotation,
        map_background,
        map_index,
        map_layers,
        map_markers,    ## DEPRECATED
        map_metadata,
        map_pathways,
        map_style,
        map_termgraph,
        vector_tiles
    ]
)

#===============================================================================
#===============================================================================
