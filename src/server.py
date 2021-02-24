#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019  David Brooks
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
import logging
import os.path
import pathlib
import sqlite3
import sys
import time

#===============================================================================

import flask
from flask import Blueprint, Flask, Response, request
from flask_cors import CORS

#===============================================================================

try:
    from werkzeug.wsgi import FileWrapper
except ImportError:
    FileWrapper = None

def send_bytes(bytes_io, mimetype):
    if FileWrapper is not None:
        return Response(FileWrapper(bytes_io), mimetype=mimetype, direct_passthrough=True)
    else:
        return flask.send_file(bytes_io, mimetype=mimetype)

#===============================================================================

def send_json(filename):
    try:
        return flask.send_file(filename)
    except FileNotFoundError:
        return flask.jsonify({})


#===============================================================================

# Global settings

from .settings import settings
settings['ROOT_PATH'] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]

def normalise_path(path):
#========================
    return os.path.normpath(os.path.join(settings['ROOT_PATH'], path))

FLATMAP_ROOT = os.environ.get('FLATMAP_ROOT', './flatmaps')
settings['FLATMAP_ROOT'] = normalise_path(FLATMAP_ROOT)
settings['ONTOLOGY_ROOT'] = normalise_path('./ontology')

settings['BEARER_TOKENS'] = os.environ.get('BEARER_TOKENS', '').split()

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

    from .maker import Manager

    map_maker = Manager()

#===============================================================================

def blank_tile():
    tile = Image.new('RGBA', (1, 1), color=(255, 255, 255, 0))
    file = io.BytesIO()
    tile.save(file, 'png')
    file.seek(0)
    return file

#===============================================================================

flatmap_blueprint = Blueprint('flatmap', __name__,
                                root_path=settings['ROOT_PATH'],
                                url_prefix='/')


maker_blueprint = Blueprint('maker', __name__, url_prefix='/make')

@maker_blueprint.before_request
def maker_auth_check():
    if not settings['BEARER_TOKENS']:
        return None  # no security defined; permit all access.
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        if auth.split()[1] in settings['BEARER_TOKENS']:
            return None
    return flask.make_response('{"error": "unauthorized"}', 403)


viewer_blueprint = Blueprint('viewer', __name__,
                             root_path=normalise_path('./viewer/dist'),
                             url_prefix='/viewer')

#===============================================================================

def wsgi_app(viewer=False):
    settings['MAP_VIEWER'] = viewer
    app = Flask(__name__)
    CORS(flatmap_blueprint)
    app.register_blueprint(flatmap_blueprint)
    app.register_blueprint(maker_blueprint)
    app.register_blueprint(viewer_blueprint)
    if __name__ != '__main__':
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
    if not viewer and not settings['BEARER_TOKENS']:
        # Only warn once...
        app.logger.warning('No bearer tokens defined')
    return app

#===============================================================================

def normalise_identifier(id):
#============================
    return ':'.join([(s[:-1].lstrip('0') + s[-1])
                        for s in id.split(':')])

#===============================================================================

def metadata(tile_reader, name):
    try:
        row = tile_reader._query("SELECT value FROM metadata WHERE name='{}';".format(name)).fetchone()
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return {} if row is None else json.loads(row[0])

def get_metadata(map_id, name):
    mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
    return metadata(MBTilesReader(mbtiles), name)

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
        for tile_dir in root_path.iterdir():
            mbtiles = os.path.join(settings['FLATMAP_ROOT'], tile_dir, 'index.mbtiles')
            if os.path.isdir(tile_dir) and os.path.exists(mbtiles):
                reader = MBTilesReader(mbtiles)
                try:
                    source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
                except (InvalidFormatError, sqlite3.OperationalError):
                    flask.abort(404, 'Cannot read tile database: {}'.format(mbtiles))
                if source_row is not None:
                    flatmap = { 'id': tile_dir.name, 'source': source_row[0] }
                    created = reader._query("SELECT value FROM metadata WHERE name='created';").fetchone()
                    if created is not None:
                        flatmap['created'] = created[0]
                    describes = reader._query("SELECT value FROM metadata WHERE name='describes';").fetchone()
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

@flatmap_blueprint.route('flatmap/<string:map_id>/tilejson')
def tilejson(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'tilejson.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/style')
def style(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'style.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/styled')
def styled(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'styled.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/markers')
def markers(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'markers.json')
    return send_json(filename)

'''
@flatmap_blueprint.route('flatmap/<string:map_id>/metadata')
def map_metadata(map_id):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'metadata.ttl')
    if os.path.exists(filename):
        return flask.send_file(filename, mimetype='text/turtle')
    else:
        flask.abort(404, 'Missing RDF metadata')
'''

@flatmap_blueprint.route('flatmap/<string:map_id>/layers')
def map_layers(map_id):
    return flask.jsonify(get_metadata(map_id, 'layers'))

@flatmap_blueprint.route('flatmap/<string:map_id>/metadata')
@flatmap_blueprint.route('flatmap/<string:map_id>/annotations')
def map_annotations(map_id):
    return flask.jsonify(get_metadata(map_id, 'annotations'))

@flatmap_blueprint.route('flatmap/<string:map_id>/pathways')
def map_pathways(map_id):
    return flask.jsonify(get_metadata(map_id, 'pathways'))

@flatmap_blueprint.route('flatmap/<string:map_id>/images/<string:image>')
def map_background(map_id, image):
    filename = os.path.join(settings['FLATMAP_ROOT'], map_id, 'images', image)
    if os.path.exists(filename):
        return flask.send_file(filename)
    else:
        flask.abort(404, 'Missing image: {}'.format(filename))

@flatmap_blueprint.route('flatmap/<string:map_id>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_id, z, y, x):
    try:
        mbtiles = os.path.join(settings['FLATMAP_ROOT'], map_id, 'index.mbtiles')
        tile_reader = MBTilesReader(mbtiles)
        tile_bytes = tile_reader.tile(z, x, y)
        if metadata(tile_reader, 'compressed'):
            tile_bytes = gzip.decompress(tile_bytes)
        return send_bytes(io.BytesIO(tile_bytes), 'application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return flask.make_response('', 204)

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

@flatmap_blueprint.route('ontology/<string:ontology>')
def send_ontology(ontology):
    filename = os.path.join(settings['ONTOLOGY_ROOT'], ontology)
    if os.path.exists(filename):
        return flask.send_file(filename, mimetype='application/rdf+xml'
                                        if os.path.splitext(filename)[1] in ['.owl', '.xml']
                                        else None)
    else:
        flask.abort(404, 'Missing file: {}'.format(filename))

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
        app.logger.error('No source specified in data')
        flask.abort(501, 'No source specified in data')
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

@viewer_blueprint.route('/')
@viewer_blueprint.route('/<path:filename>')
def viewer(filename='index.html'):
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

app = wsgi_app()

def viewer():
    return wsgi_app(True)

#===============================================================================
