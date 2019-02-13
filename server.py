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

import os.path
import logging
from flask import Flask, abort, request, send_file
from flask_restful import Resource, Api
from flask_expects_json import expects_json

#===============================================================================

options = {}
if __name__ == '__main__':
    import os
    options['HTML_ROOT'] = os.getcwd()
    options['STATIC_ROOT'] = os.path.join(os.getcwd(), '..')
else:
    options['HTML_ROOT'] = '/www/html/celldl/flatmaps/demo'
    options['STATIC_ROOT'] = '/www/html/celldl/flatmaps/demo'

app = Flask(__name__, static_folder=os.path.join(options['STATIC_ROOT'], 'static'))

#===============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    app.logger.debug("Sending index")
    return send_file(os.path.join(options['HTML_ROOT'], 'index.html'))

@app.route('/<path>', methods=['GET', 'POST'])
def serve(path):
    if not path:
        path = 'index.html'
    file = os.path.join(options['HTML_ROOT'], path)
    app.logger.debug("Sending %s", file)
    return send_file(file)

@app.route('/<map>/features/', methods=['GET', 'POST'])
def mapfeatures(map):
    filename = os.path.join(options['STATIC_ROOT'], map, 'features.json')
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        abort(404)

@app.route('/<map>/features/<layer>', methods=['GET', 'POST'])
def layer_features(map, layer):
    filename = os.path.join(options['STATIC_ROOT'], map, 'features', '%s.json' % layer)
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        abort(404)

@app.route('/<map>/tiles/<layer>/<z>/<x>/<y>', methods=['GET', 'POST'])
def tiles(map, layer, z, y, x):
    filename = os.path.join(options['STATIC_ROOT'], map, 'tiles', layer, z, x, '%s.png' % y)
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        return send_file(os.path.join(options['STATIC_ROOT'], 'static/images/blank.png'))

@app.route('/<map>/topology/', methods=['GET', 'POST'])
def maptopology(map):
    filename = os.path.join(options['STATIC_ROOT'], map, 'topology.json')
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
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

    """
    database = os.path.join(options['LOCATION'], map, 'annotation.sqlite')

    SQLAlchemy model??

    location table:
        uri, location

    GET:
        return URI's location (200 OK, 404)
    PUT:
        add/update URI's location (201 Created, 200 OK)
    DELETE:
        remove URI (204 No Content, 404)

    Abbreviate URIs??  `ilx:XXXX`

    Set Last-Modified and ETag when sending responses, updating


    """
#===============================================================================

api = Api(app)

api.add_resource(Features, '/<map>/features')
api.add_resource(Feature,  '/<map>/feature/<uri>')

#===============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=8000)

#===============================================================================
