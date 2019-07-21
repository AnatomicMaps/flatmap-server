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
import time

#===============================================================================

from flask import abort, Blueprint, Flask, jsonify, make_response, request, send_file
from flask_cors import CORS

from landez.sources import MBTilesReader, ExtractionError

#===============================================================================


#===============================================================================

flatmap_blueprint = Blueprint('flatmap', __name__, url_prefix='/', static_folder='static',
                               root_path=os.path.dirname(os.path.abspath(__file__)))

flatmaps_root = os.path.join(flatmap_blueprint.root_path, '../flatmaps')

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
            source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
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

@flatmap_blueprint.route('flatmap/<string:map_path>/style')
def style(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'style.json')
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/annotations')
def map_annotations(map_path):
    filename = os.path.join(flatmaps_root, map_path, 'annotations.ttl')
    if os.path.exists(filename):
        response = make_response(send_file(filename))
        response.headers['Content-Type'] = 'text/turtle'
        return response
    else:
        abort(404, 'Missing RDF annotations')

@flatmap_blueprint.route('flatmap/<string:map_path>/metadata', methods=['GET', 'POST'])
def map_metadata(map_path):
    mbtiles = os.path.join(flatmaps_root, map_path, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    annotations_row = reader._query("SELECT value FROM metadata WHERE name='annotations';").fetchone()
    if annotations_row is None:
        annotations = {}
    else:
        annotations = json.loads(annotations_row[0])
    if request.method == 'GET':
        return jsonify(annotations)
    elif request.method == 'POST':                      # Authentication... <===========
        source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
        map_source = source_row[0] if source_row is not None else ''
        old_annotations = json.dumps(annotations)
        annotations = json.dumps(request.get_json())    # Validation...     <===========
        reader._query("REPLACE into metadata(name, value) VALUES('annotations', ?);", (annotations,))
        reader._query("COMMIT")
        audit(remote_addr(request), old_annotations, annotations)
        return 'Annotations updated'

@flatmap_blueprint.route('flatmap/<string:map_path>/images/<string:image>')
def map_background(map_path, image):
    filename = os.path.join(flatmaps_root, map_path, 'images', image)
    return send_file(filename)

@flatmap_blueprint.route('flatmap/<string:map_path>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map_path, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map_path, 'index.mbtiles')
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='application/octet-stream')
    except ExtractionError:
        pass
    return make_response('', 204)

@flatmap_blueprint.route('flatmap/<string:map_path>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map_path, layer, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map_path, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png')
    except ExtractionError:
        pass
    return make_response('', 204)

#===============================================================================

app = Flask(__name__)

app.register_blueprint(flatmap_blueprint)

CORS(app)

#===============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='A web-server for flatmaps.')
    parser.add_argument('--debug', action='store_true',
                        help="run in debugging mode (NOT FOR PRODUCTION)")
    parser.add_argument('--port', type=int, metavar='PORT', default=4329,
                        help='the port to listen on (default 4329)')

    args = parser.parse_args()

    app.run(debug=args.debug, host='localhost', port=args.port)

#===============================================================================
