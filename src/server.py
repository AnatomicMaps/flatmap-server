#===============================================================================
#
#  Flatmap viewer and annotation tool
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

import io
import json
import os.path
import pathlib
import sqlite3
import time

#===============================================================================

from flask import abort, Blueprint, Flask, jsonify, make_response, request, send_file
from flask_cors import CORS

from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

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

def get_metadata(map_path, name):
    mbtiles = os.path.join(root_paths['flatmaps'], map_path, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    try:
        row = reader._query("SELECT value FROM metadata WHERE name='{}';".format(name)).fetchone()
    except (InvalidFormatError, sqlite3.OperationalError):
        abort(404, 'Cannot read tile database')
    return {} if row is None else json.loads(row[0])

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
                abort(404, 'Cannot read tile database')
            if source_row is not None:
                flatmap = { 'id': tile_dir.name, 'source': source_row[0] }
                created = reader._query("SELECT value FROM metadata WHERE name='created';").fetchone()
                if created is not None:
                    flatmap['created'] = created[0]
                describes = reader._query("SELECT value FROM metadata WHERE name='describes';").fetchone()
                if describes is not None:
                    flatmap['describes'] = normalise_identifier(describes[0])
                flatmap_list.append(flatmap)
    return jsonify(flatmap_list)

@flatmap_blueprint.route('flatmap/<string:map_path>/')
def map(map_path):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'index.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/tilejson')
def tilejson(map_path):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'tilejson.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/style')
def style(map_path):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'style.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/styled')
def styled(map_path):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'styled.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/annotations')
def map_annotations(map_path):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'annotations.ttl')
    if os.path.exists(filename):
        return send_file(filename, mimetype='text/turtle')
    else:
        abort(404, 'Missing RDF annotations')

@flatmap_blueprint.route('flatmap/<string:map_path>/layers')
def map_layers(map_path):
    return jsonify(get_metadata(map_path, 'layers'))

@flatmap_blueprint.route('flatmap/<string:map_path>/metadata')
def map_metadata(map_path):
    return jsonify(get_metadata(map_path, 'annotations'))

@flatmap_blueprint.route('flatmap/<string:map_path>/pathways')
def map_pathways(map_path):
    return jsonify(get_metadata(map_path, 'pathways'))

@flatmap_blueprint.route('flatmap/<string:map_path>/images/<string:image>')
def map_background(map_path, image):
    filename = os.path.join(root_paths['flatmaps'], map_path, 'images', image)
    if os.path.exists(filename):
        return send_file(filename)
    else:
        abort(404, 'Missing image: {}'.format(filename))

@flatmap_blueprint.route('flatmap/<string:map_path>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_path, z, y, x):
    try:
        mbtiles = os.path.join(root_paths['flatmaps'], map_path, 'index.mbtiles')
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='application/octet-stream')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        abort(404, 'Cannot read tile database')
    return make_response('', 204)

@flatmap_blueprint.route('flatmap/<string:map_path>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map_path, layer, z, y, x):
    try:
        mbtiles = os.path.join(root_paths['flatmaps'], map_path, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png')
    except ExtractionError:
        pass
    except (InvalidFormatError, sqlite3.OperationalError):
        abort(404, 'Cannot read tile database')
    return send_file(blank_tile(), mimetype='image/png')

@flatmap_blueprint.route('ontology/<string:ontology>')
def send_ontology(ontology):
    filename = os.path.join(root_paths['ontologies'], ontology)
    if os.path.exists(filename):
        return send_file(filename, mimetype='application/rdf+xml'
                                        if os.path.splitext(filename)[1] in ['.owl', '.xml']
                                        else None)
    else:
        abort(404, 'Missing file: {}'.format(filename))

#===============================================================================

app.register_blueprint(flatmap_blueprint)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='A web-server for flatmaps.')
    parser.add_argument('--debug', action='store_true',
                        help="run in debugging mode (NOT FOR PRODUCTION)")
    parser.add_argument('--map-dir', metavar='MAP_DIR', default='./flatmaps',
                        help='top-level directory containing flatmaps')
    parser.add_argument('--port', type=int, metavar='PORT', default=4329,
                        help='the port to listen on (default 4329)')

    args = parser.parse_args()

    set_root_path('flatmaps', args.map_dir)

    app.run(debug=args.debug, host='localhost', port=args.port)

#===============================================================================
