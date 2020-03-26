#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g
from flask_restful import Resource, abort
from bson import ObjectId

from .lib import register_resource


@register_resource('/exchanges', '/exchanges/<int:exchange_id>')
class ExchangeResource(Resource):

    def get(self, exchange_id: str = None):
        if exchange_id:
            exchange = g.db.exchanges.find_one(ObjectId(exchange_id))
            if not exchange:
                abort(404, message='exchange does not exist')
            return exchange

        # TODO check user has access to exchange
        return list(g.db.exchanges.find())
