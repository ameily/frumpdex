#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g
from flask_restful import Resource, abort
from bson import ObjectId

from .lib import register_resource


@register_resource('/stocks', '/stocks/<int:stock_id>')
class ExchangeResource(Resource):

    def get(self, stock_id: str = None):
        if stock_id:
            stock = g.db.stocks.find_one(ObjectId(stock_id))
            if not stock:
                abort(404, message='stock does not exist')
            return stock

        # TODO scope to user's exchange
        return list(g.db.stocks.find())
