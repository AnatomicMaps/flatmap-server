import os.path
from flask import Flask, send_file

options = {'LOCATION': '/www/html/celldl/flatmaps'}
app = Flask(__name__, static_url_path='%s/static' % options['LOCATION'])

@app.route('/<map>/tiles/<layer>/<z>/<x>/<y>', methods=['GET', 'POST'])
def tiles(map, layer, z, y, x):
    filename = os.path.join(options['LOCATION'], map, 'tiles', layer, z, x, '%s.png' % y)
    app.logger.debug("Checking %s", filename)
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        return send_file(os.path.join(options['LOCATION'], 'static/images/blank.png'))

@app.route('/<map>', methods=['GET', 'POST'])
def index(map):
    return send_file(os.path.join(options['LOCATION'], map, 'index.html'))

if __name__ == '__main__':
    import os
    options['LOCATION'] = os.getcwd()
    app.run(debug=True, host='localhost', port=8000)
