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

from flask import abort, Blueprint, Flask, jsonify, request, send_file

from landez.sources import MBTilesReader, ExtractionError

#===============================================================================

from knowledgebase import KnowledgeBase

#===============================================================================

map_core_blueprint = Blueprint('map_core', __name__, url_prefix='/', static_folder='static',
                               root_path='/Users/dave/build/flatmap-mvt-viewer/dist')

flatmaps_root = os.path.join(map_core_blueprint.root_path, '../maps')

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

def allow_cross_origin(response):
#================================
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

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
        mbtiles = os.path.join(flatmaps_root, path, 'index.mbtiles')
        if os.path.isdir(path) and os.path.exists(mbtiles):
            reader = MBTilesReader(mbtiles)
            source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
            if source_row is not None:
                map = { 'id': path.name, 'source': source_row[0] }
                created = reader._query("SELECT value FROM metadata WHERE name='created';").fetchone()
                if created is not None:
                    map['created'] = created[0]
                describes = reader._query("SELECT value FROM metadata WHERE name='describes';").fetchone()
                if describes is not None:
                    map['describes'] = describes[0]
                maps.append(map)
    return allow_cross_origin(jsonify(maps))

@map_core_blueprint.route('flatmap/<string:map>/')
def map(map):
    filename = os.path.join(flatmaps_root, map, 'index.json')
    return allow_cross_origin(send_file(filename))

@map_core_blueprint.route('flatmap/<string:map>/style')
def style(map):
    filename = os.path.join(flatmaps_root, map, 'style.json')
    return allow_cross_origin(send_file(filename))

@map_core_blueprint.route('flatmap/<string:map>/annotations', methods=['GET', 'POST'])
def map_annotations(map):
    mbtiles = os.path.join(flatmaps_root, map, 'index.mbtiles')
    reader = MBTilesReader(mbtiles)
    annotations_row = reader._query("SELECT value FROM metadata WHERE name='annotations';").fetchone()
    if annotations_row is None:
        annotations = {}
    else:
        annotations = json.loads(annotations_row[0])
    if request.method == 'GET':
        return allow_cross_origin(jsonify(annotations))
    elif request.method == 'POST':                      # Authentication... <===========
        source_row = reader._query("SELECT value FROM metadata WHERE name='source';").fetchone()
        map_source = source_row[0] if source_row is not None else ''
        old_annotations = json.dumps(annotations)
        annotations = json.dumps(request.get_json())    # Validation...     <===========
        reader._query("REPLACE into metadata(name, value) VALUES('annotations', ?);", (annotations,))
        reader._query("COMMIT")
        audit(remote_addr(request), old_annotations, annotations)
        return 'Annotations updated'

@map_core_blueprint.route('flatmap/<string:map>/images/<string:image>')
def map_background(map, image):
    filename = os.path.join(flatmaps_root, map, 'images', image)
    return allow_cross_origin(send_file(filename))

@map_core_blueprint.route('flatmap/<string:map>/mvtiles/<int:z>/<int:x>/<int:y>')
def vector_tiles(map, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map, 'index.mbtiles')
        reader = MBTilesReader(mbtiles)
        return allow_cross_origin(send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='application/octet-stream'))
    except ExtractionError:
        pass
    return ('', 204)

@map_core_blueprint.route('flatmap/<string:map>/tiles/<string:layer>/<int:z>/<int:x>/<int:y>')
def image_tiles(map, layer, z, y, x):
    try:
        mbtiles = os.path.join(flatmaps_root, map, '{}.mbtiles'.format(layer))
        reader = MBTilesReader(mbtiles)
        return allow_cross_origin(send_file(io.BytesIO(reader.tile(z, x, y)), mimetype='image/png'))
    except ExtractionError:
        pass
    return ('', 204)

@map_core_blueprint.route('query', methods=['POST'])
def kb_query():
    query = request.get_json()
    try:
        with KnowledgeBase(os.path.join(flatmaps_root, 'KnowledgeBase.sqlite')) as graph:
            return allow_cross_origin(jsonify(graph.query(query.get('sparql'))))
    except RuntimeError:
        abort(404, 'Cannot open knowledge base')

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
