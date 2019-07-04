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

from flask import abort, Blueprint, Flask, jsonify, request, send_file

from landez.sources import MBTilesReader, ExtractionError

#===============================================================================

from contextlib import ContextDecorator

import rdflib

import rdflib_sqlalchemy as sqlalchemy
sqlalchemy.registerplugins()

from rdflib.plugins.sparql.results.jsonlayer import encode as JSON_results_encode
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer

#===============================================================================

from namespaces import SCICRUNCH_NS

#===============================================================================

class KnowledgeBase(rdflib.Graph, ContextDecorator):
    def __init__(self, kb_path):
        SPARC = rdflib.URIRef('SPARC')
        store = rdflib.plugin.get('SQLAlchemy', rdflib.store.Store)(identifier=SPARC)
        super().__init__(store, identifier=SPARC)
        self.namespace_manager = SCICRUNCH_NS
        database = rdflib.Literal('sqlite:///{}'.format(kb_path))
        self.open(database)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def query(self, sparql, **kwds):
        results = {}
        try:
            query_results = super().query(sparql, **kwds)
            json_results = JSONResultSerializer(query_results)
            if json_results.result.type == 'ASK':
                results['head'] = {}
                results['boolean'] = json_results.result.askAnswer
            else:                       # SELECT
                results['head'] = { 'vars': json_results.result.vars }
                results['results'] = { 'bindings': [
                    json_results._bindingToJSON(x) for x in json_results.result.bindings
                ]}
        except:
            pass
        return JSON_results_encode(results)

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
        rows = reader._query("SELECT value FROM metadata WHERE name='annotations';").fetchone()
        if rows is None:
            annotations = {}
        else:
            annotations = json.loads(rows[0])
        return jsonify(annotations)
    elif request.method == 'POST':                      # Authentication... <===========
        annotations = json.dumps(request.get_json())    # Validation...     <===========
        reader._query("UPDATE metadata SET value=? WHERE name='annotations';", [annotations])
        reader._query("COMMIT")
        return 'Annotations updated'

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

@map_core_blueprint.route('query', methods=['POST'])
def kb_query():
    sparql = request.get_json()
    try:
        with KnowledgeBase(os.path.join(flatmaps_root, 'KnowledgeBase.sqlite')) as graph:
            return jsonify(graph.query(sparql.get('query')))
    except RuntimeError:
        abort(404, 'Cannot open knowledgebase')

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
