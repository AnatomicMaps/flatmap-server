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

#===============================================================================

from flask import Blueprint, Flask, jsonify, request, send_file

from landez.sources import MBTilesReader, ExtractionError

#===============================================================================

map_core_blueprint = Blueprint('map_core', __name__, url_prefix='/', static_folder='static',
                               root_path='/Users/dave/build/flatmap-mvt-viewer/dist')

flatmaps_root = os.path.join(map_core_blueprint.root_path, '../maps')

#===============================================================================

@map_core_blueprint.route('/')
@map_core_blueprint.route('/<string:filepath>')
def serve(filepath=None):
    if not filepath: filepath = 'index.html'
    filename = os.path.join(map_core_blueprint.root_path, filepath)
    return send_file(filename)

@map_core_blueprint.route('flatmap/')
def maps():
    maps = []
    for path in pathlib.Path(flatmaps_root).iterdir():
        if os.path.isdir(path) and os.path.join(flatmaps_root, path, 'index.mbtiles'):
            mbtiles = os.path.join(flatmaps_root, path, 'index.mbtiles')
            reader = MBTilesReader(mbtiles)
            rows = reader._query("SELECT value FROM metadata WHERE name='source';")
            maps.append({ 'id': path.name, 'source': [row[0] for row in rows][0] })
    return jsonify(maps)

@map_core_blueprint.route('flatmap/<string:map>/')
def map(map):
    filename = os.path.join(flatmaps_root, map, 'index.json')
    return send_file(filename)

@map_core_blueprint.route('flatmap/<string:map>/style')
def style(map):
    filename = os.path.join(flatmaps_root, map, 'style.json')
    return send_file(filename)

@map_core_blueprint.route('flatmap/<string:map>/annotations', methods=['GET', 'POST'])
def map_annotations(map):
    mbtiles = os.path.join(flatmaps_root, map, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    if request.method == 'GET':
        rows = reader._query("SELECT value FROM metadata WHERE name='annotations';")
        annotations = json.loads([row[0] for row in rows][0])
        return jsonify(annotations)
@map_core_blueprint.route('flatmap/<string:map>/images/<string:image>')
def map_background(map, image):
    filename = os.path.join(flatmaps_root, map, 'images', image)
    return send_file(filename)

@map_core_blueprint.route('flatmap/<string:map>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map, 'index.mbtiles')
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='application/octet-stream')
    except ExtractionError:
        pass
    return ('', 204)

@map_core_blueprint.route('flatmap/<string:map>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map, layer, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png')
    except ExtractionError:
        pass
    return ('', 204)

#===============================================================================

app = Flask(__name__)

app.register_blueprint(map_core_blueprint)

#===============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='A web-server for flatmaps.')
    parser.add_argument('--debug', action='store_true',
                        help="run in debugging mode (NOT FOR PRODUCTION)")
    parser.add_argument('--port', type=int, metavar='PORT', default=5000,
                        help='the port to listen on (default 5000)')

    args = parser.parse_args()

    app.run(debug=args.debug, host='localhost', port=args.port)

#===============================================================================
