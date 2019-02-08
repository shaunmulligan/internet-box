from sanic import Sanic
from sanic.response import json
from sanic.log import logger
from sanic.response import text

import nm

app = Sanic('connectivity')

@app.route("/")
async def index(request):
    logger.info('request to /')
    return json({"hello": "world"})

@app.route("/connections")
async def active_connections(request):
    logger.info('request to /connections')
    return json(nm.get_active_connections())

@app.route("/connections/state")
async def get_connectivity_state(request):
    logger.info('request to /connections/state')
    return json(nm.get_global_state())

@app.route("/accesspoint/<interface:[A-z0-9]{0,4}>/toggle")
async def toggle_access_point(request):
    
    return json({"status":"up"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80,debug=True, access_log=True)
