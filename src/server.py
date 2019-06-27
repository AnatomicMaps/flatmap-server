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
import logging

#===============================================================================

from flask import Flask, abort, request, send_file
from flask_restful import Resource, Api
from flask_expects_json import expects_json

#===============================================================================

import mbtiles
from options import options

#===============================================================================

if __name__ == '__main__':
    import os
    options['HTML_ROOT'] = os.path.join(os.getcwd(), '../dist')
    options['MAP_ROOT'] = os.path.join(os.getcwd(), '../maps')
    options['LOG_FILE'] = os.path.join(os.getcwd(), 'debug.log')
else:
    options['HTML_ROOT'] = '/www/html/celldl/flatmaps/demo'
    options['MAP_ROOT'] = '/www/html/celldl/flatmaps/demo/maps'
    options['LOG_FILE'] = '/www/flatmaps/debug.log'

app = Flask(__name__)


#===============================================================================

@app.route('/', methods=['GET'])
@app.route('/<path>', methods=['GET'])
def serve(path=None):
    if not path:
        path = 'index.html'
    filename = os.path.join(options['HTML_ROOT'], path)
    if os.path.isfile(filename):
        return send_file(filename)
    abort(404)


@app.route('/<map>/', methods=['GET'])
def map(map):
    filename = os.path.join(options['MAP_ROOT'], map, 'index.json')
    if os.path.isfile(filename):
#        metadata_store.load(map)
        return send_file(filename)
    abort(404)


@app.route('/<map>/style', methods=['GET'])
def style(map):
    filename = os.path.join(options['MAP_ROOT'], map, 'style.json')
    if os.path.isfile(filename):
        return send_file(filename)
    abort(404)


@app.route('/<map>/features/', methods=['GET', 'POST', 'PUT'])
@app.route('/<map>/features/<layer>', methods=['GET', 'POST', 'PUT'])
def map_features(map, layer=None):
    if layer:
        filename = os.path.join(options['MAP_ROOT'], map, 'features', '%s.json' % layer)
    else:
        filename = os.path.join(options['MAP_ROOT'], map, 'features.json')
    if request.method == 'GET':
        if os.path.isfile(filename):
            return send_file(filename)
        abort(404)
    elif request.method == 'POST':      # Authentication... <===========
        geoJson = request.get_json()    # Validation...     <===========
        with open(filename, 'w') as f:
            json.dump(geoJson, f)
        return 'Features updated'
    elif request.method == 'PUT':      # Authentication... <===========
        geoJson = request.get_json()    # Validation...     <===========
        with open(filename, 'w') as f:
            json.dump(geoJson, f, indent=2)   # User option for indent?? Or when debugging??
        return ('Features created', 204)


@app.route('/<map>/images/<image>', methods=['GET'])
def map_background(map, image):
    filename = os.path.join(options['MAP_ROOT'], map, 'images', image)
    if os.path.isfile(filename):
        return send_file(filename)
    abort(404)


@app.route('/<map>/mvtiles/<z>/<x>/<y>', methods=['GET'])
def vector_tiles(map, z, y, x):
    try:
        return send_file(io.BytesIO(mbtiles.get_vector_tile(map, z, x, y)), mimetype='application/octet-stream')
    except mbtiles.ExtractionError:
        pass
    return ('', 204)


@app.route('/<map>/tiles/<layer>/<z>/<x>/<y>', methods=['GET'])
def map_tiles(map, layer, z, y, x):
    try:
        return send_file(io.BytesIO(mbtiles.get_raster_tile(map, layer, z, x, y)), mimetype='image/png')
    except mbtiles.ExtractionError:
        pass
    return ('', 204)


@app.route('/<map>/topology/', methods=['GET'])
def map_topology(map):
    filename = os.path.join(options['MAP_ROOT'], map, 'topology.json')
    if os.path.isfile(filename):
        return send_file(filename)
    abort(404)

#===============================================================================

location_schema = {
    'type': 'object',
    'properties': {
        'location': {
            'type': 'array',
            'minItems': 2,
            'maxItems': 2,
            'items': {
                'type': 'number'
            }
        }
    },
    'required': ['location']
}

#===============================================================================

class Features(Resource):

    _store = {}

    def get(self, map):
        return (Features._store, 200)

#===============================================================================

class Feature(Resource):
    def get(self, map, uri):
        if uri in Features._store:
            return ({'location': Features._store[uri]}, 200)
        else:
            abort(404)

    @expects_json(location_schema)
    def put(self, map, uri):
        status = 200 if uri in Features._store else 201
        data = request.get_json()
        Features._store[uri] = data['location']
        return ({'location': Features._store[uri]}, status)

    def delete(self, map, uri):
        if uri in Features._store:
            del Features._store[uri]
            return ('', 204)
        else:
            abort(404)

#===============================================================================

api = Api(app)

api.add_resource(Features, '/<map>/features')
api.add_resource(Feature,  '/<map>/feature/<uri>')

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
