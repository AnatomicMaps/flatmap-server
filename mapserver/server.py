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

import gzip
import io
import json
import os
import os.path
import pathlib
import sqlite3
import sys

#===============================================================================

import flask
from flask import Blueprint, Flask, Response, request
from flask_cors import CORS

try:
    from werkzeug.wsgi import FileWrapper
except ImportError:
    FileWrapper = None

#===============================================================================

from .knowledgestore import KnowledgeStore
from . import __version__

#===============================================================================

# Global settings

from .settings import settings
settings['ROOT_PATH'] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]

def normalise_path(path):
#========================
    return os.path.normpath(os.path.join(settings['ROOT_PATH'], path))

#===============================================================================

FLATMAP_ROOT = os.environ.get('FLATMAP_ROOT', './flatmaps')
settings['FLATMAP_ROOT'] = normalise_path(FLATMAP_ROOT)

settings['BEARER_TOKENS'] = os.environ.get('BEARER_TOKENS', '').split()

MAPMAKER_ROOT = os.environ.get('MAPMAKER_ROOT', './mapmaker')
settings['MAPMAKER_ROOT'] = normalise_path(MAPMAKER_ROOT)
# Do we have a copy of ``mapmaker`` available?
HAVE_MAPMAKER = pathlib.Path(os.path.join(settings['MAPMAKER_ROOT'],
                                          'mapmaker/__init__.py')).exists()

#===============================================================================

# Needed to read JPEG 2000 files with OpenCV2 under Linux

os.environ['OPENCV_IO_ENABLE_JASPER'] = '1'

#===============================================================================

# Don't import unnecessary packages when building documentation as otherwise
# a ``readthedocs`` build aborts with ``excessive memory consumption``

if 'sphinx' not in sys.modules:
    from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError
    from PIL import Image

    # We also don't instantiate a Manager as doing so will prevent Sphinx from
    # exiting (and hang a ``readthedocs`` build)

    if HAVE_MAPMAKER:
        sys.path.insert(0, settings['MAPMAKER_ROOT'])
        from .maker import Manager
        map_maker = Manager()
else:
    map_maker = None

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
def maker_auth_check():
    if map_maker is not None:
        if not settings['BEARER_TOKENS']:
            return None  # no security defined; permit all access.
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            if auth.split()[1] in settings['BEARER_TOKENS']:  #### not in ?????
                return None
    return flask.make_response('{"error": "unauthorized"}', 403, {'mimetype': 'application/json'})

#===============================================================================

viewer_blueprint = Blueprint('viewer', __name__,
                             root_path=normalise_path('./viewer/dist'),
                             url_prefix='/viewer')

#===============================================================================
#===============================================================================

app = None

#===============================================================================

def wsgi_app(viewer=False):
    global app
    settings['MAP_VIEWER'] = viewer
    app = Flask('mapserver')
    app.config['CORS_HEADERS'] = 'Content-Type'
    CORS(annotator_blueprint)
    app.register_blueprint(annotator_blueprint)
    CORS(flatmap_blueprint)
    app.register_blueprint(flatmap_blueprint)
    CORS(knowledge_blueprint)
    app.register_blueprint(knowledge_blueprint)
    app.register_blueprint(maker_blueprint)
    app.register_blueprint(viewer_blueprint)

    settings['LOGGER'].info(f'Started flatmap server version {__version__}')
    if not settings['BEARER_TOKENS']:
        # Only warn once...
        settings['LOGGER'].warning('No bearer tokens defined')

    # Open our knowledge base
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'], create=True)
    if knowledge_store.error is not None:
        settings['LOGGER'].error('{}: {}'.format(knowledge_store.error, knowledge_store.db_name))

    return app

#===============================================================================
#===============================================================================

def send_bytes(bytes_io, mimetype):
    if FileWrapper is not None:
        return Response(FileWrapper(bytes_io), mimetype=mimetype, direct_passthrough=True)
    else:
        return flask.send_file(bytes_io, mimetype=mimetype)

#===============================================================================

def send_json(filename):
#=======================
    try:
        return flask.send_file(filename)
    except FileNotFoundError:
        return flask.jsonify({})

#===============================================================================

def error_abort(msg):
#====================
    settings['LOGGER'].error(msg)
    flask.abort(501, msg)

#===============================================================================

def blank_tile():
    tile = Image.new('RGBA', (1, 1), color=(255, 255, 255, 0))
    file = io.BytesIO()
    tile.save(file, 'png')
    file.seek(0)
    return file

#===============================================================================

def normalise_identifier(id):
#============================
    return ':'.join([(s[:-1].lstrip('0') + s[-1])
                        for s in id.split(':')])

#===============================================================================

def read_metadata(tile_reader, name):
    try:
        row = tile_reader._query("SELECT value FROM metadata WHERE name='{}'".format(name)).fetchone()
    except (InvalidFormatError, sqlite3.OperationalError):
        raise IOError('Cannot read tile database')
    return {} if row is None else json.loads(row[0])

def get_metadata(map_id, name):
    mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
    return read_metadata(MBTilesReader(mbtiles), name)

#===============================================================================
#===============================================================================

@flatmap_blueprint.route('/')
def maps():
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
            if os.path.isdir(flatmap_dir) and os.path.exists(index) and os.path.exists(mbtiles):
                with open(index) as fp:
                    index = json.loads(fp.read())
                version = index.get('version', 1.0)
                reader = MBTilesReader(mbtiles)
                if version >= 1.3:
                    metadata: dict[str, str] = read_metadata(reader, 'metadata')
                    if (('id' not in metadata or flatmap_dir.name != metadata['id'])
                     and ('uuid' not in metadata or flatmap_dir.name != metadata['uuid'].split(':')[-1])):
                        settings['LOGGER'].error(f'Flatmap id mismatch: {flatmap_dir}')
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
                    flatmap['uri'] = f'{flask.request.root_url}{flatmap_blueprint.name}/{id}/'
                    if 'created' in metadata:
                        flatmap['created'] = metadata['created']
                    if 'taxon' in metadata:
                        flatmap['taxon'] = normalise_identifier(metadata['taxon'])
                        flatmap['describes'] = metadata['describes'] if 'describes' in metadata else flatmap['taxon']
                    elif 'describes' in metadata:
                        flatmap['taxon'] = normalise_identifier(metadata['describes'])
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
                        flask.abort(404, 'Cannot read tile database: {}'.format(mbtiles))
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
                        flatmap['describes'] = normalise_identifier(describes[0])
                flatmap_list.append(flatmap)
    return flask.jsonify(flatmap_list)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/')
def map(map_id):
    """
    Return a representation of a flatmap.

    :param map_id: The flatmap identifier
    :type map_id: string

    :reqheader Accept: Determines the response content

    If an SVG representation of the map exists and the :mailheader:`Accept` header
    doesn't specify a JSON response then the SVG is returned, otherwise the
    flatmap's ``index.json`` is returned.
    """
    if 'json' not in flask.request.accept_mimetypes.best:
        filename = os.path.join(settings['FLATMAP_ROOT'], map_id, '{}.svg'.format(map_id))
        if os.path.exists(filename):
            return flask.send_file(filename, mimetype='image/svg+xml')
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.json')
    return send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/tilejson')
def tilejson(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'tilejson.json')
    return send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/style')
def style(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'style.json')
    return send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/styled')
def styled(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'styled.json')
    return send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/markers')
def markers(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'markers.json')
    return send_json(filename)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/layers')
def map_layers(map_id):
    try:
        return flask.jsonify(get_metadata(map_id, 'layers'))
    except IOError as err:
        flask.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/metadata')
def map_metadata(map_id):
    try:
        return flask.jsonify(get_metadata(map_id, 'metadata'))
    except IOError as err:
        flask.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/pathways')
def map_pathways(map_id):
    try:
        return flask.jsonify(get_metadata(map_id, 'pathways'))
    except IOError as err:
        flask.abort(404, str(err))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/images/<string:image>')
def map_background(map_id, image):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'images', image)
    if os.path.exists(filename):
        return flask.send_file(filename)
    else:
        flask.abort(404, 'Missing image: {}'.format(filename))

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_id, z, y, x):
    try:
        mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
        tile_reader = MBTilesReader(mbtiles)
        tile_bytes = tile_reader.tile(z, x, y)
        if read_metadata(tile_reader, 'compressed'):
            tile_bytes = gzip.decompress(tile_bytes)
        return send_bytes(io.BytesIO(tile_bytes), 'application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return flask.make_response('', 204)

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map_id, layer, z, y, x):
    try:
        mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        image_bytes = io.BytesIO(reader.tile(z, x, y))
        return send_bytes(image_bytes, 'image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return send_bytes(blank_tile(), 'image/png')

#===============================================================================

@flatmap_blueprint.route('flatmap/<string:map_id>/annotations')
def map_annotation(map_id):
    try:
        return flask.jsonify(get_metadata(map_id, 'annotations'))
    except IOError as err:
        flask.abort(404, str(err))

#===============================================================================
#===============================================================================

@knowledge_blueprint.route('label/<string:entity>')
def knowledge_label(entity: str):
    """
    Find an entity's label from the flatmap server's knowledge base.
    """
    knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'], create=False, read_only=False)
    label = knowledge_store.label(entity)
    knowledge_store.close()
    return flask.jsonify({'entity': entity, 'label': label})

@knowledge_blueprint.route('query/', methods=['POST'])
def knowledge_query():
    """
    Query the flatmap server's knowledge base.

    :<json string sql: SQL code to execute
    :<jsonarr string params: any parameters for the query

    :>json array(string) keys: column names of result values
    :>json array(array(string)) values: result data rows
    :>json string error: any error message
    """
    params = flask.request.get_json()
    if params is None or 'sql' not in params:
        return flask.jsonify({'error': 'No SQL specified in request'})
    else:
        knowledge_store = KnowledgeStore(settings['FLATMAP_ROOT'], create=False, read_only=True)
        result = knowledge_store.query(params.get('sql'), params.get('params', []))
        knowledge_store.close()
        if 'error' in result:
            settings['LOGGER'].warning('SQL: {}'.format(result['error']))
        return flask.jsonify(result)

#===============================================================================
#===============================================================================

@maker_blueprint.route('/map', methods=['POST'])
def make_map():
    """
    Generate a flatmap.

    :<json string source: the map's manifest

    :>json int process: the id of the map generation process
    :>json string map: the unique identifier for the map
    :>json string source: the map's manifest
    :>json string status: the status of the map generation process
    """
    params = flask.request.get_json()
    if params is None or 'source' not in params:
        error_abort('No source specified in data')
    map_source = params.get('source')
    maker_process = map_maker.make(map_source)
    s = {
        'process': maker_process.process_id,
        'map': maker_process.map_id,
        'source': map_source,
        'status': 'started'
    }
    return flask.jsonify(s)

@maker_blueprint.route('/log/<int:process_id>')
def make_log(process_id):
    """
    Return the log file of a map generation process.

    :param process_id: The id of a maker process
    :type process_id: int
    """
    filename = map_maker.logfile(process_id)
    if os.path.exists(filename):
        return flask.send_file(filename)
    else:
        flask.abort(404, 'Missing log file')

@maker_blueprint.route('/status/<int:process_id>')
def make_status(process_id):
    """
    Get the status of a map generation process.

    :param process_id: The id of a maker process
    :type process_id: int

    :>json int maker: the id of the map generation process
    :>json string status: the status of the map generation process
    """
    return flask.jsonify({
        'process': process_id,
        'status': map_maker.status(process_id)
    })

#===============================================================================
#===============================================================================

@viewer_blueprint.route('/')
@viewer_blueprint.route('/<path:filename>')
def viewer_app(filename='index.html'):
    """
    The flatmap viewer application.

    .. :quickref: viewer; Get the flatmap viewer application

    :param filename: The viewer file to get, defaults to ``index.html``
    :type filename: path
    """
    filename = os.path.join(viewer_blueprint.root_path, filename)
    if settings['MAP_VIEWER'] and os.path.exists(filename):
        return flask.send_file(filename)
    else:
        flask.abort(404)

#===============================================================================
#===============================================================================

# Add annotator routes
from .annotator import authenticate, unauthenticate
from .annotator import annotated_items, annotations, annotation, add_annotation

#===============================================================================
#===============================================================================

def server():
    return wsgi_app(False)

def viewer():
    return wsgi_app(True)

#===============================================================================
#===============================================================================
