import os.path
from flask import Flask, abort, request, send_file
from flask_restful import Resource, Api
from flask_expects_json import expects_json

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

options = {}
if __name__ == '__main__':
    import os
    options['LOCATION'] = os.getcwd()
else:
    options['LOCATION'] = '/www/html/celldl/flatmaps'

app = Flask(__name__, static_folder='%s/static' % options['LOCATION'])
api = Api(app)


@app.route('/<map>', methods=['GET', 'POST'])
@app.route('/<map>/', methods=['GET', 'POST'])
def index(map):
    app.logger.debug("Sending index")
    return send_file(os.path.join(options['LOCATION'], map, 'index.html'))

@app.route('/<map>/<path>', methods=['GET', 'POST'])
def serve(map, path):
    if not path:
        path = 'index.html'
    file = os.path.join(options['LOCATION'], map, path)
    app.logger.debug("Sending %s", file)
    return send_file(file)

@app.route('/<map>/json/<layer>', methods=['GET', 'POST'])
def json(map, layer):
    filename = os.path.join(options['LOCATION'], map, 'json', '%s.json' % layer)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        abort(404)

@app.route('/<map>/tiles/<layer>/<z>/<x>/<y>', methods=['GET', 'POST'])
def tiles(map, layer, z, y, x):
    filename = os.path.join(options['LOCATION'], map, 'tiles', layer, z, x, '%s.png' % y)
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        return send_file(os.path.join(options['LOCATION'], 'static/images/blank.png'))


annotations = {}

class Annotations(Resource):
    def get(self, map):
        return (annotations, 200)

class Annotation(Resource):
    def get(self, map, uri):
        if uri in annotations:
            return ({'location': annotations[uri]}, 200)
        else:
            abort(404)

    @expects_json(location_schema)
    def put(self, map, uri):
        status = 200 if uri in annotations else 201
        data = request.get_json()
        annotations[uri] = data['location']
        return ({'location': annotations[uri]}, status)

    def delete(self, map, uri):
        if uri in annotations:
            del annotations[uri]
            return ('', 204)
        else:
            abort(404)

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

api.add_resource(Annotations, '/<map>/annotations')
api.add_resource(Annotation,  '/<map>/annotation/<uri>')


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=8000)
