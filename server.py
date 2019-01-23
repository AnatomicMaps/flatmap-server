import os.path
from flask import Flask, send_file

LOCATION = '/www/html/celldl/flatmaps'

app = Flask(__name__, static_url_path='%s/static' % LOCATION)

@app.route('/<map>/tiles/<layer>/<z>/<x>/<y>', methods=['GET', 'POST'])
def tiles(map, layer, z, y, x):
    filename = '%s/%s/tiles/%s/%s/%s/%s.png' % (LOCATION, map, layer, z, x, y)
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        return send_file('%s/tiles/blank.png' % LOCATION)

@app.route('/<map>', methods=['GET', 'POST'])
def index(map):
    return send_file('%s/%s/index.html' % (LOCATION, map))

if __name__ == '__main__':
    app.run(debug=False, host='localhost', port=8000)
