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
import os.path
import pathlib
import sqlite3
import time

#===============================================================================

import flask
from flask import Blueprint, Flask
from flask_cors import CORS

from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

#===============================================================================

from .generator import Manager
generator = Manager()

#===============================================================================

from PIL import Image

def blank_tile():
    tile = Image.new('RGBA', (1, 1), color=(255, 255, 255, 0))
    file = io.BytesIO()
    tile.save(file, 'png')
    file.seek(0)
    return file

#===============================================================================

flatmap_blueprint = Blueprint('flatmap', __name__, url_prefix='/', static_folder='static',
                               root_path=os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])


#===============================================================================

root_paths = {
    'flatmaps': os.path.normpath(os.path.join(flatmap_blueprint.root_path, './flatmaps')),
    'ontologies': os.path.normpath(os.path.join(flatmap_blueprint.root_path, './ontology')),
    }

def set_root_path(id, path):
#===========================
    global root_paths
    root_paths[id] = os.path.normpath(os.path.join(flatmap_blueprint.root_path, path))

#===============================================================================

app = Flask(__name__)

CORS(flatmap_blueprint)

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
    mbtiles = os.path.join(root_paths['flatmaps'], map_id, 'index.mbtiles')
    return metadata(MBTilesReader(mbtiles), name)

#===============================================================================

def send_json(filename):
    try:
        return flask.send_file(filename)
    except FileNotFoundError:
        return flask.jsonify({})

#===============================================================================

@flatmap_blueprint.route('/')
def maps():
    flatmap_list = []
    for tile_dir in pathlib.Path(root_paths['flatmaps']).iterdir():
        mbtiles = os.path.join(root_paths['flatmaps'], tile_dir, 'index.mbtiles')
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

@flatmap_blueprint.route('flatmap/<string:map_id>/')
def map(map_id):
    if 'json' not in flask.request.accept_mimetypes.best:
        filename = os.path.join(root_paths['flatmaps'], map_id, '{}.svg'.format(map_id))
        if os.path.exists(filename):
            return flask.send_file(filename, mimetype='image/svg+xml')
    filename = os.path.join(root_paths['flatmaps'], map_id, 'index.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/tilejson')
def tilejson(map_id):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'tilejson.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/style')
def style(map_id):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'style.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/styled')
def styled(map_id):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'styled.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/markers')
def markers(map_id):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'markers.json')
    return send_json(filename)

@flatmap_blueprint.route('flatmap/<string:map_id>/annotations')
def map_annotations(map_id):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'annotations.ttl')
    if os.path.exists(filename):
        return flask.send_file(filename, mimetype='text/turtle')
    else:
        flask.abort(404, 'Missing RDF annotations')

@flatmap_blueprint.route('flatmap/<string:map_id>/layers')
def map_layers(map_id):
    return flask.jsonify(get_metadata(map_id, 'layers'))

@flatmap_blueprint.route('flatmap/<string:map_id>/metadata')
def map_metadata(map_id):
    return flask.jsonify(get_metadata(map_id, 'annotations'))

@flatmap_blueprint.route('flatmap/<string:map_id>/pathways')
def map_pathways(map_id):
    return flask.jsonify(get_metadata(map_id, 'pathways'))

@flatmap_blueprint.route('flatmap/<string:map_id>/images/<string:image>')
def map_background(map_id, image):
    filename = os.path.join(root_paths['flatmaps'], map_id, 'images', image)
    if os.path.exists(filename):
        return flask.send_file(filename)
    else:
        flask.abort(404, 'Missing image: {}'.format(filename))

@flatmap_blueprint.route('flatmap/<string:map_id>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_id, z, y, x):
    try:
        mbtiles = os.path.join(root_paths['flatmaps'], map_id, 'index.mbtiles')
        tile_reader = MBTilesReader(mbtiles)
        tile_bytes = tile_reader.tile(z, x, y)
        if metadata(tile_reader, 'compressed'):
            tile_bytes = gzip.decompress(tile_bytes)
        return flask.send_file(io.BytesIO(tile_bytes), mimetype='application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return flask.make_response('', 204)

@flatmap_blueprint.route('flatmap/<string:map_id>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map_id, layer, z, y, x):
    try:
        mbtiles = os.path.join(root_paths['flatmaps'], map_id, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return flask.send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        flask.abort(404, 'Cannot read tile database')
    return flask.send_file(blank_tile(), mimetype='image/png')

@flatmap_blueprint.route('ontology/<string:ontology>')
def send_ontology(ontology):
    filename = os.path.join(root_paths['ontologies'], ontology)
    if os.path.exists(filename):
        return flask.send_file(filename, mimetype='application/rdf+xml'
                                        if os.path.splitext(filename)[1] in ['.owl', '.xml']
                                        else None)
    else:
        flask.abort(404, 'Missing file: {}'.format(filename))


@flatmap_blueprint.route('generate/map', methods=['POST'])
def generate_map():
    options = flask.request.get_json()
    options['outputDir'] = root_paths['flatmaps']
    process_id = generator.generate(options)
    return flask.jsonify({
        'process': process_id,
        'status': 'started',
        'options': options
    })

@flatmap_blueprint.route('generate/status/<int:process_id>')
def generate_status(process_id):
    return flask.jsonify({
        'process': process_id,
        'status': generator.status(process_id)
    })

#===============================================================================

app.register_blueprint(flatmap_blueprint)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='A web-server for flatmaps.')
    parser.add_argument('--debug', action='store_true',
                        help="run in debugging mode (NOT FOR PRODUCTION)")
    parser.add_argument('--map-dir', metavar='MAP_DIR', default='./flatmaps',
                        help='top-level directory containing flatmaps (default `./flatmaps`)')
    parser.add_argument('--port', type=int, metavar='PORT', default=4329,
                        help='the port to listen on (default 4329)')

    args = parser.parse_args()

    set_root_path('flatmaps', args.map_dir)

    app.run(debug=args.debug, host='localhost', port=args.port)

#===============================================================================
