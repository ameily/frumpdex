#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import logging
import sys
import json

from flask import Flask, g, request, session, Blueprint, Response
from flask.json import JSONEncoder
from flask_restful import Api
from bson import ObjectId

from .db import FrumpdexDatabase
from .api.lib import serialize_extra_types, get_registered_resources
from .views.lib import get_blueprints

logger = logging.getLogger('frumpdex')


class FrumpdexJsonEncoder(JSONEncoder):

    def default(self, o):
        return serialize_extra_types(o, default=super().default)



app = Flask(__name__)
api = Api(app)

app.secret_key = b'\x89i\xc1\x1f 8B?\xbd\x0b\x95\xa7;0\xd2K'
app.json_encoder = FrumpdexJsonEncoder


@api.representation('application/json')
def api_json_serializer(data, code, headers=None):
    return Response(json.dumps(data, default=serialize_extra_types), code,
                    mimetype='application/json')


@app.before_request
def before_request():
    g.db = FrumpdexDatabase.instance()

    token = session.get('token')
    header_auth = request.headers.get('Authorization')
    if not token and header_auth:
        parts = header_auth.split(' ', 1)
        if len(parts) == 2 and parts[0] == 'Bearer':
            token = parts[1]

    g.user = g.db.users.find_one({'token': token}) if token else None
    g.exchange = g.db.exchanges.find_one({'_id': g.user['exchange_id']}) if g.user else None


def register_apis():
    for resource_cls, endpoints in get_registered_resources():
        logger.debug(f'registering API resource {resource_cls}: {endpoints}')
        api.add_resource(resource_cls, *[f'/api/v1/{ep.strip("/")}' for ep in endpoints])


def register_views():
    for blueprint in get_blueprints():
        logger.debug(f'registering view: {blueprint.name}')
        app.register_blueprint(blueprint)


def setup_logging(debug: bool):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)



def run_server(debug: bool = False, host: str = '127.0.0.1', port: int = 5000):
    setup_logging(debug)

    db = FrumpdexDatabase.instance()
    db.connect()

    register_apis()
    register_views()

    app.run(debug=debug, host=host, port=port)


if __name__ == '__main__':
    run_server(debug=True)
