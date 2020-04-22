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

flatmap_blueprint = Blueprint('flatmap', __name__, url_prefix='/', static_folder='static',
                               root_path=os.path.dirname(os.path.abspath(__file__)))

flatmaps_root = os.path.normpath(os.path.join(flatmap_blueprint.root_path, '../flatmaps'))
ontology_root = os.path.normpath(os.path.join(flatmap_blueprint.root_path, '../ontology'))

#===============================================================================

app = Flask(__name__)

CORS(flatmap_blueprint)

#===============================================================================

class Annotator(object):
    def __init__(self):
        self._annotating = False

    def enable(self, state):
        self._annotating = True

    def enabled(self):
        return self._annotating

annotator = Annotator();

#===============================================================================

def remote_addr(req):
#====================
    if req.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return req.environ['REMOTE_ADDR']
    else:
        return req.environ['HTTP_X_FORWARDED_FOR']

def audit(user_ip, old_value, new_value):
#========================================
    with open(os.path.join(flatmaps_root, 'audit.log'), 'a') as aud:
        aud.write('{}\n'.format(json.dumps({
            'time': time.asctime(),
            'ip': user_ip,
            'old': old_value,
            'new': new_value
        })))

#===============================================================================

@flatmap_blueprint.route('/')
def maps():
    flatmap_list = []
    for tile_dir in pathlib.Path(flatmaps_root).iterdir():
        mbtiles = os.path.join(flatmaps_root, tile_dir, 'index.mbtiles')
        if os.path.isdir(tile_dir) and os.path.exists(mbtiles):
            reader = MBTilesReader(mbtiles)
            try:
                source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
            except InvalidFormatError:
                abort(404, 'Cannot read tile database')
            if source_row is not None:
                flatmap = { 'id': tile_dir.name, 'source': source_row[0] }
                created = reader._query("SELECT value FROM metadata WHERE name='created';").fetchone()
                if created is not None:
                    flatmap['created'] = created[0]
                describes = reader._query("SELECT value FROM metadata WHERE name='describes';").fetchone()
                if describes is not None:
                    flatmap['describes'] = describes[0]
                flatmap_list.append(flatmap)
    return jsonify(flatmap_list)

@flatmap_blueprint.route('flatmap/<string:map_path>/')
def map(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'index.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/tilejson')
def tilejson(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'tilejson.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/style')
def style(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'style.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/styled')
def styled(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'styled.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/annotations')
def map_annotations(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'annotations.ttl')
    if os.path.exists(filename):
        return send_file(filename, mimetype='text/turtle')
    else:
        abort(404, 'Missing RDF annotations')

@flatmap_blueprint.route('flatmap/<string:map_path>/layers')
def map_layers(map_path):
    mbtiles = os.path.join(flatmaps_root, map_path, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    try:
        layers_row = reader._query("SELECT value FROM metadata WHERE name='layers';").fetchone()
    except InvalidFormatError:
        abort(404, 'Cannot read tile database')
    if layers_row is None:
        layers = {}
    else:
        layers = json.loads(layers_row[0])
    return jsonify(layers)

@flatmap_blueprint.route('flatmap/<string:map_path>/metadata', methods=['GET', 'POST'])
def map_metadata(map_path):
    mbtiles = os.path.join(flatmaps_root, map_path, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    try:
        annotations_row = reader._query("SELECT value FROM metadata WHERE name='annotations';").fetchone()
    except InvalidFormatError:
        abort(404, 'Cannot read tile database')
    if annotations_row is None:
        annotations = {}
    else:
        annotations = json.loads(annotations_row[0])
    if request.method == 'GET':
        return jsonify(annotations)
    elif not annotator.enabled():
        abort(405, 'Invalid method')
    elif request.method == 'POST':                      # Authentication... <===========
        source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
        map_source = source_row[0] if source_row is not None else ''
        old_annotations = json.dumps(annotations)
        annotations = json.dumps(request.get_json())    # Validation...     <===========
        reader._query("REPLACE into metadata(name, value) VALUES('annotations', ?);", (annotations,))
        reader._query("COMMIT")
        audit(remote_addr(request), old_annotations, annotations)
        return 'Metadata updated'

@flatmap_blueprint.route('flatmap/<string:map_path>/images/<string:image>')
def map_background(map_path, image):
    filename = os.path.join(flatmaps_root, map_path, 'images', image)
    if os.path.exists(filename):
        return send_file(filename)
    else:
        abort(404, 'Missing image: {}'.format(filename))

@flatmap_blueprint.route('flatmap/<string:map_path>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_path, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map_path, 'index.mbtiles')
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
        mbtiles = os.path.join(flatmaps_root, map_path, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png')
    except ExtractionError:
        pass
    except InvalidFormatError:
        abort(404, 'Cannot read tile database')
    return make_response('', 204)

@flatmap_blueprint.route('ontology/<string:ontology>')
def send_ontology(ontology):
    filename = os.path.join(ontology_root, ontology)
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
    parser.add_argument('--annotate', action='store_true',
                        help="allow local annotation (NOT FOR PRODUCTION)")
    parser.add_argument('--debug', action='store_true',
                        help="run in debugging mode (NOT FOR PRODUCTION)")
    parser.add_argument('--port', type=int, metavar='PORT', default=4329,
                        help='the port to listen on (default 4329)')

    args = parser.parse_args()

    annotator.enable(args.annotate)

    app.run(debug=args.debug, host='localhost', port=args.port)

#===============================================================================
