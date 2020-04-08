#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import logging
import sys
import json
from typing import List, Optional

from flask import Flask, g, request, session, Blueprint, Response
import flask.json
from flask_restful import Api
from flask_socketio import SocketIO, join_room, leave_room
from bson import ObjectId
from cincoconfig import Config

from .db import FrumpdexDatabase
from .api.lib import serialize_extra_types, get_registered_resources
from .views.lib import get_blueprints
from .config import config

logger = logging.getLogger('frumpdex')


class FrumpdexJsonEncoder(flask.json.JSONEncoder):
    '''
    Handles JSON serializing extra types (datetime and ObjectId).
    '''

    def default(self, o):
        return serialize_extra_types(o, default=super().default)


app = Flask(__name__)
api = Api(app)

app.secret_key = b'\x89i\xc1\x1f 8B?\xbd\x0b\x95\xa7;0\xd2K'
app.json_encoder = FrumpdexJsonEncoder

socketio = SocketIO(app, json=flask.json)


@api.representation('application/json')
def api_json_serializer(data, code, headers=None) -> Response:
    '''
    Handles JSON serialization from the REST API.
    '''
    return Response(json.dumps(data, default=serialize_extra_types), code,
                    mimetype='application/json')


def get_request_user(db: FrumpdexDatabase) -> Optional[dict]:
    '''
    Get the user for the active request. Looks at either the header "Authorization Bearer" token or
    if the user is already authenticated in the session.

    :returns: the user from object the database if the token is valid
    '''
    token = session.get('token')
    header_auth = request.headers.get('Authorization')
    if not token and header_auth:
        parts = header_auth.split(' ', 1)
        if len(parts) == 2 and parts[0] == 'Bearer':
            token = parts[1]

    return db.users.find_one({'token': token}) if token else None


@app.before_request
def before_request() -> None:
    '''
    Populate the global ``g`` object
    '''
    g.db = FrumpdexDatabase.instance()
    g.socketio = socketio

    g.user = get_request_user(g.db)
    g.exchange = g.db.exchanges.find_one({'_id': g.user['exchange_id']}) if g.user else None


@socketio.on('connect')
def handle_connect() -> None:
    '''
    Authenticate a user attempting to connect to the web socket.
    '''
    user = get_request_user(FrumpdexDatabase.instance())
    if not user:
        raise ConnectionRefusedError('unauthorized')


@socketio.on('join')
def handle_join_room(data) -> None:
    '''
    Authenticate the user attempting to join a web socket room and verify that they have proper
    authorization (belong to the correct Exchange).
    '''
    room = data["room"]
    user = get_request_user(FrumpdexDatabase.instance())

    if room.startswith('exchange.'):
        exchange_id = room.split('.', 1)[1]
        if user and exchange_id == str(user['exchange_id']):
            logger.debug(f'join room: {room}')
            join_room(room)


@socketio.on('leave')
def handle_leave_room(data):
    '''
    Websocket client leave room.
    '''
    logger.debug(f'leave room: {data["room"]}')
    leave_room(data['room'])


def register_apis() -> None:
    '''
    Register the REST API endpoints (flask_restful Resources).
    '''
    for resource_cls, endpoints in get_registered_resources():
        logger.debug(f'registering API resource {resource_cls}: {endpoints}')
        api.add_resource(resource_cls, *[f'/api/v1/{ep.strip("/")}' for ep in endpoints])


def register_views() -> None:
    '''
    Register the views.
    '''
    for blueprint in get_blueprints():
        logger.debug(f'registering view: {blueprint.name}')
        app.register_blueprint(blueprint)


def setup_logging(logfile: str, debug: bool, silent: bool) -> None:
    '''
    Setup logging.

    :param logfile: save logs to a file
    :param debug: set log level to debug
    :param silent: don't print anything to stdout/stderr
    '''
    fmt = '[%(asctime)s] %(levelname)s: %(message)s'
    if not silent:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    if logfile:
        handler = logging.FileHandler(logfile, 'a')
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def run_server(cfg: Config):
    '''
    Run the frumpdex server.
    '''
    setup_logging(cfg.logfile, debug=cfg.is_debug_mode, silent=cfg.silent)

    db = FrumpdexDatabase.instance()
    db.connect(cfg.mongodb.url)

    register_apis()
    register_views()

    if cfg.http.cors.allowed_origins:
        # is this a hack? idk
        socketio.server.eio.cors_allowed_origins = cfg.http.cors.allowed_origins

    logger.info(f'starting frumpdex server: http://{cfg.http.address}:{cfg.http.port}')
    socketio.run(app, debug=cfg.is_debug_mode, host=cfg.http.address, port=cfg.http.port)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='web server listening port', action='store',
                        dest='http.port')
    parser.add_argument('-H', '--host', help='web server listening address', action='store',
                        dest='http.address')
    parser.add_argument('--debug', action='store_const', help='debug mode', dest='mode',
                        const='debug')
    parser.add_argument('-l', '--log', action='store', help='log file')
    parser.add_argument('-s', '--silent', action='store_true', help='disable console output')
    parser.add_argument('-m', '--mongo-url', action='store', help='MongoDB URI',
                        dest='mongodb.url')
    parser.add_argument('--cors-allowed-origins', action='append',
                        dest='http.cors.allowed_origins',
                        help='list of CORS allowed origins, can be specified multiple times')
    parser.add_argument('-c', '--config', action='store',
                        help='load YAML configuration file, additional command line parameters '
                             'will override configuration file settings')

    args = parser.parse_args()
    if args.config:
        config.load(args.config, format='yaml')

    config.cmdline_args_override(args, ignore=['config'])

    run_server(config)
