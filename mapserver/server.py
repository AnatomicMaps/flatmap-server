#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-2023  David Brooks
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

from datetime import datetime
import gzip
import io
import json
import os
import os.path
import pathlib
import sqlite3
import sys

#===============================================================================

import quart
from quart import Blueprint, Quart, request
from quart_cors import cors

#===============================================================================

from .knowledge import KnowledgeStore, get_metadata, read_metadata
from .knowledge.hierarchy import AnatomicalHierarchy, CACHED_SPARC_HIERARCHY
from .settings import settings
from . import __version__

#===============================================================================

# Global settings

settings['ROOT_PATH'] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]

def normalise_path(path):
#========================
    return os.path.normpath(os.path.join(settings['ROOT_PATH'], path))

#===============================================================================

FLATMAP_ROOT = os.environ.get('FLATMAP_ROOT', './flatmaps')
settings['FLATMAP_ROOT'] = normalise_path(FLATMAP_ROOT)
if not os.path.exists(settings['FLATMAP_ROOT']):
    exit(f'Missing {settings["FLATMAP_ROOT"]} directory -- set FLATMAP_ROOT environment variable to the full path and/or create directory')

FLATMAP_VIEWER = os.environ.get('FLATMAP_VIEWER', './viewer')
settings['FLATMAP_VIEWER'] = normalise_path(FLATMAP_VIEWER)

FLATMAP_SERVER_LOGS = os.environ.get('FLATMAP_SERVER_LOGS', './logs')
settings['FLATMAP_SERVER_LOGS'] = normalise_path(FLATMAP_SERVER_LOGS)
if not os.path.exists(settings['FLATMAP_SERVER_LOGS']):
    exit(f'Missing {settings["FLATMAP_SERVER_LOGS"]} directory -- set FLATMAP_SERVER_LOGS environment variable to the full path and/or create directory')

MAPMAKER_LOGS = os.environ.get('MAPMAKER_LOGS', os.path.join(FLATMAP_SERVER_LOGS, 'mapmaker'))
settings['MAPMAKER_LOGS'] = normalise_path(MAPMAKER_LOGS)

#===============================================================================

# Bearer tokens for service authentication

settings['ANNOTATOR_TOKENS'] = os.environ.get('ANNOTATOR_TOKENS', '').split()
settings['MAPMAKER_TOKENS'] = os.environ.get('MAPMAKER_TOKENS', '').split()

#===============================================================================
"""
If a file with this name exists in the map's output directory then the map
is in the process of being made
"""
MAKER_SENTINEL = '.map_making'

#===============================================================================

# Needed to read JPEG 2000 files with OpenCV2 under Linux

os.environ['OPENCV_IO_ENABLE_JASPER'] = '1'

#===============================================================================

# Build and cache a hierarchy of anataomical terms used by a flatmap

anatomical_hierarchy = AnatomicalHierarchy()

#===============================================================================

# Don't import unnecessary packages nor instantiate a Manager when building
# documentation as otherwise a ``readthedocs`` build either hangs or aborts
# with ``excessive memory consumption``

map_maker = None

if 'sphinx' not in sys.modules:
    from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError
    from PIL import Image

#===============================================================================

flatmap_blueprint = Blueprint('flatmap', __name__,
                                root_path=settings['ROOT_PATH'],
                                url_prefix='/')

#===============================================================================

annotator_blueprint = Blueprint('annotator', __name__,
                                root_path=settings['ROOT_PATH'],
                                url_prefix='/annotator')

#===============================================================================

knowledge_blueprint = Blueprint('knowledge', __name__, url_prefix='/knowledge')

#===============================================================================

maker_blueprint = Blueprint('maker', __name__, url_prefix='/make')

@maker_blueprint.before_request
async def maker_auth_check():
    if map_maker is not None:
        if not settings['MAPMAKER_TOKENS']:
            return None  # no security defined; permit all access.
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            if auth.split()[1] in settings['MAPMAKER_TOKENS']:
                return None
    return await quart.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})

#===============================================================================

viewer_blueprint = Blueprint('viewer', __name__,
                             root_path=os.path.join(settings['FLATMAP_VIEWER'], 'app/dist'),
                             url_prefix='/viewer')

connectivity_blueprint = Blueprint('connectivity', __name__,
                             root_path=os.path.join(normalise_path('./connectivity'), 'dist'),
                             url_prefix='/connectivity-graph')

#===============================================================================
#===============================================================================

def query_knowledge(sql: str, params: list[str]) -> dict:
#========================================================
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'])
    result = knowledge_store.query(sql, params) if knowledge_store else {
                'error': 'Knowledge Store not available'
             }
    knowledge_store.close()
    return result

def get_knowledge_sources() -> list[str]:
#========================================
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'])
    sources = knowledge_store.knowledge_sources() if knowledge_store else []
    knowledge_store.close()
    return sources

#===============================================================================

async def send_json(filename):
#=============================
    try:
        return await quart.send_file(filename, mimetype='application/json')
    except FileNotFoundError:
        return quart.jsonify({})

#===============================================================================

def error_abort(msg):
#====================
    app.logger.error(msg)
    quart.abort(501, msg)

#===============================================================================

def blank_tile():
    tile = Image.new('RGBA', (1, 1), color=(255, 255, 255, 0))
    file = io.BytesIO()
    tile.save(file, 'png')
    file.seek(0)
    return file

#===============================================================================
#===============================================================================

@flatmap_blueprint.route('/')
async def maps():
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
            index = os.path.join(settings['FLATMAP_ROOT'], flatmap_dir, 'index.json')
            mbtiles = os.path.join(settings['FLATMAP_ROOT'], flatmap_dir, 'index.mbtiles')
            map_making = os.path.join(settings['FLATMAP_ROOT'], flatmap_dir, MAKER_SENTINEL)
            if (os.path.isdir(flatmap_dir) and not os.path.exists(map_making)
            and os.path.exists(index) and os.path.exists(mbtiles)):
                with open(index) as fp:
                    index = json.loads(fp.read())
                version = index.get('version', 1.0)
                reader = MBTilesReader(mbtiles)
                if version >= 1.3:
                    metadata: dict[str, str] = read_metadata(reader, 'metadata')
                    if (('id' not in metadata or flatmap_dir.name != metadata['id'])
                     and ('uuid' not in metadata or flatmap_dir.name != metadata['uuid'].split(':')[-1])):
                        app.logger.error(f'Flatmap id mismatch: {flatmap_dir}')
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
                    flatmap['uri'] = f'{quart.request.root_url}{flatmap_blueprint.name}/{id}/'
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
                        source_row = reader._query("SELECT value FROM metadata WHERE name='source'").fetchone()
                    except (InvalidFormatError, sqlite3.OperationalError):
                        quart.abort(404, 'Cannot read tile database: {}'.format(mbtiles))
                    if source_row is None:
                        continue
                    flatmap = {
                        'id': flatmap_dir.name,
                        'source': source_row[0]
                    }
                    created = reader._query("SELECT value FROM metadata WHERE name='created'").fetchone()
                    if created is not None:
                        flatmap['created'] = created[0]
                    describes = reader._query("SELECT value FROM metadata WHERE name='describes'").fetchone()
                    if describes is not None and describes[0]:
                        flatmap['describes'] = describes[0]
                flatmap_list.append(flatmap)
    return quart.jsonify(flatmap_list)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/')
async def map(map_id):
    """
    Return a representation of a flatmap.

    :param map_id: The flatmap identifier
    :type map_id: string

    :reqheader Accept: Determines the response content

    If an SVG representation of the map exists and the :mailheader:`Accept` header
    doesn't specify a JSON response then the SVG is returned, otherwise the
    flatmap's ``index.json`` is returned.
    """
    index_file = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.json')
    if not os.path.exists(index_file):
        quart.abort(404, 'Missing map index')
    with open(index_file) as fp:
        index = json.load(fp)
    if 'json' not in quart.request.accept_mimetypes.best:
        svg_file = os.path.join(settings['FLATMAP_ROOT'], map_id, f'{index["id"]}.svg')
        if not os.path.exists(svg_file):
            svg_file = os.path.join(settings['FLATMAP_ROOT'], map_id, 'images', f'{index["id"]}.svg')
        if os.path.exists(svg_file):
            return await quart.send_file(svg_file, mimetype='image/svg+xml')
    return quart.jsonify(index)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/style')
async def style(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'style.json')
    return await send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/markers')
async def markers(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'markers.json')
    return await send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/layers')
async def map_layers(map_id):
    try:
        return quart.jsonify(get_metadata(map_id, 'layers'))
    except IOError as err:
        quart.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/metadata')
async def map_metadata(map_id):
    try:
        return quart.jsonify(get_metadata(map_id, 'metadata'))
    except IOError as err:
        quart.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/pathways')
async def map_pathways(map_id):
    try:
        return quart.jsonify(get_metadata(map_id, 'pathways'))
    except IOError as err:
        quart.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/images/<string:image>')
async def map_background(map_id, image):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'images', image)
    if os.path.exists(filename):
        return await quart.send_file(filename)
    else:
        quart.abort(404, 'Missing image: {}'.format(filename))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/mvtiles/<int:z>/<int:x>/<int:y>')
async def vector_tiles(map_id, z, y, x):
    try:
        mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
        tile_reader = MBTilesReader(mbtiles)
        tile_bytes = tile_reader.tile(z, x, y)
        if read_metadata(tile_reader, 'compressed'):
            tile_bytes = gzip.decompress(tile_bytes)
        return await quart.send_file(io.BytesIO(tile_bytes), mimetype='application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        quart.abort(404, 'Cannot read tile database')
    return await quart.make_response('', 204)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
async def image_tiles(map_id, layer, z, y, x):
    try:
        mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        image_bytes = io.BytesIO(reader.tile(z, x, y))
        return await quart.send_file(image_bytes, mimetype='image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        quart.abort(404, 'Cannot read tile database')
    return await quart.send_file(blank_tile(), mimetype='image/png')

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/annotations')
async def map_annotation(map_id):
    try:
        return quart.jsonify(get_metadata(map_id, 'annotations'))
    except IOError as err:
        quart.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/termgraph')
async def map_termgraph(map_id):
    try:
        return quart.jsonify(anatomical_hierarchy.get_hierachy(map_id))
    except IOError as err:
        quart.abort(404, str(err))

#===============================================================================
#===============================================================================

@knowledge_blueprint.route('query/', methods=['POST'])
async def knowledge_query():
    """
    Query the flatmap server's knowledge base.

    :<json string sql: SQL code to execute
    :<jsonarr string params: any parameters for the query

    :>json array(string) keys: column names of result values
    :>json array(array(string)) values: result data rows
    :>json string error: any error message
    """
    params = await quart.request.get_json()
    if params is None or 'sql' not in params:
        return quart.jsonify({'error': 'No SQL specified in request'})
    else:
        result = query_knowledge(params.get('sql'), params.get('params', []))
        if 'error' in result:
            app.logger.warning('SQL: {}'.format(result['error']))
        return quart.jsonify(result)

@knowledge_blueprint.route('sources')
async def knowledge_sources():
    """
    Return the knowledge sources available in the server's knowledge store.

    :>json array(string) sources: a list of knowledge sources. The list is
                                  in descending order, with the most recent
                                  source at the beginning
    """
    sources = get_knowledge_sources()
    return quart.jsonify({'sources': sources})

@knowledge_blueprint.route('sparcterms')
async def sparcterms():
    filename = os.path.join(settings['FLATMAP_ROOT'], CACHED_SPARC_HIERARCHY)
    return await send_json(filename)

@knowledge_blueprint.route('schema-version')
async def knowledge_schema_version():
    """
    :>json number version: the version of the store's schema
    """
    result = query_knowledge('select value from metadata where name=?', ['schema_version'])
    if 'error' in result:
        app.logger.warning('SQL: {}'.format(result['error']))
    return quart.jsonify({'version': result['values'][0][0]})

#===============================================================================
#===============================================================================

@maker_blueprint.route('/map', methods=['POST'])
async def make_map():
    """
    Generate a flatmap.

    :<json string source: either a local path to the map's manifest or the
                          URL of a Git repository containing the manifest
    :<json string manifest: the relative path of the map's manifest when the
                            source is a Git repository. Required in this case
    :<json string commit: the branch/tag/commit to use when the source is a
                          Git repository. Optional
    :<json boolean force: make the map regardless of whether it already exists.
                          Optional

    :>json int process: the id of the map generation process
    :>json string map: the unique identifier for the map
    :>json string source: the map's manifest
    :>json string status: the status of the map generation process
    """
    params = await quart.request.get_json()
    if params is None or 'source' not in params:
        error_abort('No source specified in data')
    if map_maker is None:
        return await quart.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})
    result = await map_maker.make(params)
    result['source'] = params.get('source')
    if 'manifest' in params:
        result['manifest'] = params['manifest']
    if 'commit' in params:
        result['commit'] = params['commit']
    return quart.jsonify(result)

@maker_blueprint.route('/process-log/<int:pid>')
async def process_log(pid: int):
    if map_maker is None:
        return await quart.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})
    log = await map_maker.full_log(pid)
    return quart.jsonify({
        'pid': pid,
        'log': log
    })

@maker_blueprint.route('/log/<string:id>')
@maker_blueprint.route('/log/<string:id>/<int:start_line>')
async def maker_log(id: str, start_line=1):
    """
    Return the status of a map generation process along with log records

    :param id: The id of a maker process
    :type id: str
    :param start_line: The line number in the log file of the first log record to return.
                       1-origin, defaults to ``1``
    :type start_line: int
    """
    if map_maker is None:
        return await quart.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})
    log_data = await map_maker.get_log(id, start_line)
    status = await map_maker.status(id)
    status['log'] = log_data
    status['stamp'] = str(datetime.now())
    return quart.jsonify(status)

@maker_blueprint.route('/status/<string:id>')
async def maker_status(id: str):
    """
    Get the status of a map generation process.

    :param id: The id of a maker process
    :type id: str

    :>json str id: the ``id`` of the map generation process
    :>json str status: the ``status`` of the generation process
    :>json int pid: the system ``process id`` of the generation process
    """
    if map_maker is None:
        return await quart.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})
    status = await map_maker.status(id)
    return quart.jsonify(status)

#===============================================================================
#===============================================================================

@viewer_blueprint.route('/')
@viewer_blueprint.route('/<path:filename>')
async def viewer_app(filename='index.html'):
    """
    The flatmap viewer application.

    .. :quickref: viewer; Get the flatmap viewer application

    :param filename: The viewer file to get, defaults to ``index.html``
    :type filename: path
    """
    filename = os.path.join(viewer_blueprint.root_path, filename)
    if settings['MAP_VIEWER'] and os.path.exists(filename):
        return await quart.send_file(filename)
    else:
        quart.abort(404)

#===============================================================================

@connectivity_blueprint.route('/')
@connectivity_blueprint.route('/<path:filename>')
async def connectivity_app(filename='index.html'):
    filename = os.path.join(connectivity_blueprint.root_path, filename)
    if os.path.exists(filename):
        return await quart.send_file(filename)
    else:
        quart.abort(404)

#===============================================================================
#===============================================================================

# Add annotator routes
from .annotator import authenticate, unauthenticate
from .annotator import annotated_items, annotations, annotation, add_annotation

#===============================================================================
#===============================================================================

app = Quart('mapserver')

cors_settings = {'allow_origin': '*'}
app = cors(app, **cors_settings)

annotator_blueprint = cors(annotator_blueprint, **cors_settings)
app.register_blueprint(annotator_blueprint)

flatmap_blueprint = cors(flatmap_blueprint, **cors_settings)
app.register_blueprint(flatmap_blueprint)

knowledge_blueprint = cors(knowledge_blueprint, **cors_settings)
app.register_blueprint(knowledge_blueprint)

app.register_blueprint(maker_blueprint)
app.register_blueprint(viewer_blueprint)
app.register_blueprint(connectivity_blueprint)

#===============================================================================
#===============================================================================

def initialise(viewer=False):
    if viewer and not os.path.exists(settings['FLATMAP_VIEWER']):
        exit(f'Missing {settings["FLATMAP_VIEWER"]} directory -- set FLATMAP_VIEWER environment variable to the full path')
    settings['MAP_VIEWER'] = viewer
    app.logger.info(f'Starting flatmap server version {__version__}')
    print(f'Starting flatmap server version {__version__}')
    if not settings['MAPMAKER_TOKENS']:
        # Only warn once...
        app.logger.warning('No bearer tokens defined')

    # Try opening our knowledge base
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'], create=True)
    if knowledge_store.error is not None:
        app.logger.error('{}: {}'.format(knowledge_store.error, knowledge_store.db_name))
    knowledge_store.close()

    if settings['MAPMAKER_TOKENS'] and 'sphinx' not in sys.modules:
        # Having a Manager prevents Sphinx from exiting and hangs a ``readthedocs`` build
        from .maker import Manager

        global map_maker
        map_maker = Manager()

#===============================================================================
#===============================================================================
