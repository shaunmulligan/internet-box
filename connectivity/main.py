from sanic import Sanic
from sanic.response import json
from sanic.log import logger
from sanic.response import text

import nm
from accesspoint import AccessPoint
from mm import ModemManager

app = Sanic('connectivity')
ap = AccessPoint()

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

@app.route("/connections/activate/<name>")
async def activate_connection(request, name):
    try:
        return json({"activated": nm.activate_connection(name) })
    except NameError as e:
        return json({"error": e})

@app.route("/accesspoint/up")
async def access_point_up(request):
    state = ap.up()
    return json({"status":state})

@app.route("/accesspoint/down")
async def access_point_down(request):
    state = ap.down()
    return json({"status":state})

if __name__ == "__main__":
    mm = ModemManager()
    m = mm.get_first()
    print(m)
    app.run(host="0.0.0.0", port=80,debug=True, access_log=True)
