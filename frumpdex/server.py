#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import Flask, g, request, session
from flask_restful import Api
from bson import ObjectId

from .db import FrumpdexDatabase


app = Flask(__name__)
api = Api(app)

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


def register_apis():
    from .api.lib import get_registered_resources
    for resource_cls, endpoints in get_registered_resources():
        api.add_resource(resource_cls, *[f'/api/v1/{ep.strip("/")}' for ep in endpoints])



if __name__ == '__main__':
    db = FrumpdexDatabase()
    db.connect()

    register_apis()

    app.run()
