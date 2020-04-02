#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import logging
import sys
import json

from flask import Flask, g, request, session, Blueprint, Response
import flask.json
from flask_restful import Api
from flask_socketio import SocketIO, join_room, leave_room
from bson import ObjectId

from .db import FrumpdexDatabase
from .api.lib import serialize_extra_types, get_registered_resources
from .views.lib import get_blueprints

logger = logging.getLogger('frumpdex')


class FrumpdexJsonEncoder(flask.json.JSONEncoder):

    def default(self, o):
        return serialize_extra_types(o, default=super().default)



app = Flask(__name__)
api = Api(app)

app.secret_key = b'\x89i\xc1\x1f 8B?\xbd\x0b\x95\xa7;0\xd2K'
app.json_encoder = FrumpdexJsonEncoder

socketio = SocketIO(app, json=flask.json)


@api.representation('application/json')
def api_json_serializer(data, code, headers=None):
    return Response(json.dumps(data, default=serialize_extra_types), code,
                    mimetype='application/json')


def get_request_user(db: FrumpdexDatabase):
    token = session.get('token')
    header_auth = request.headers.get('Authorization')
    if not token and header_auth:
        parts = header_auth.split(' ', 1)
        if len(parts) == 2 and parts[0] == 'Bearer':
            token = parts[1]

    return db.users.find_one({'token': token}) if token else None


@app.before_request
def before_request():
    g.db = FrumpdexDatabase.instance()
    g.socketio = socketio

    g.user = get_request_user(g.db)
    g.exchange = g.db.exchanges.find_one({'_id': g.user['exchange_id']}) if g.user else None


@socketio.on('connect')
def handle_connect():
    user = get_request_user(FrumpdexDatabase.instance())
    if not user:
        raise ConnectionRefusedError('unauthorized')


@socketio.on('join')
def handle_join_room(data):
    room = data["room"]
    user = get_request_user(FrumpdexDatabase.instance())

    if room.startswith('exchange.'):
        exchange_id = room.split('.', 1)[1]
        if user and exchange_id == str(user['exchange_id']):
            logger.debug(f'join room: {room}')
            join_room(room)


@socketio.on('leave')
def handle_leave_room(data):
    logger.debug(f'leave room: {data["room"]}')
    leave_room(data['room'])



def register_apis():
    for resource_cls, endpoints in get_registered_resources():
        logger.debug(f'registering API resource {resource_cls}: {endpoints}')
        api.add_resource(resource_cls, *[f'/api/v1/{ep.strip("/")}' for ep in endpoints])


def register_views():
    for blueprint in get_blueprints():
        logger.debug(f'registering view: {blueprint.name}')
        app.register_blueprint(blueprint)


def setup_logging(logfile: str, debug: bool, silent: bool):
    fmt = '[%(asctime)s] %(levelname)s: %(message)s'
    if not silent:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    if logfile:
        handler = logging.FileHandler(logfile, 'a')
        handler.setFormatter(logging.Formatter(fmt))

    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def run_server(debug: bool = False, host: str = '127.0.0.1', port: int = 5000,
               logfile: str = None, silent: bool = False, mongo_uri: str = None):
    setup_logging(logfile, debug=debug, silent=silent)

    db = FrumpdexDatabase.instance()
    db.connect(mongo_uri)

    register_apis()
    register_views()

    logger.info(f'starting frumpdex server: http://{host}:{port}')
    socketio.run(app, debug=debug, host=host, port=port)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000, help='web server listening port',
                        action='store')
    parser.add_argument('-H', '--host', default='127.0.0.1', help='web server listening address',
                        action='store')
    parser.add_argument('--debug', action='store_true', help='debug mode')
    parser.add_argument('-l', '--log', action='store', help='log file', dest='logfile')
    parser.add_argument('-s', '--silent', action='store_true', help='disable console output')
    parser.add_argument('-m', '--mongo-uri', action='store', help='MongoDB URI',
                        default='mongodb://localhost:27017')

    args = parser.parse_args()
    run_server(debug=args.debug, host=args.host, port=args.port, logfile=args.logfile,
               silent=args.silent, mongo_uri=args.mongo_uri)
