#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g
from flask_restful import Resource, abort
from bson import ObjectId

from .lib import register_resource, auth_required, parse_time_window_query


@register_resource('/exchange')
class ExchangeResource(Resource):

    @auth_required
    def get(self):
        return g.db.exchanges.find_one(ObjectId(g.user['exchange_id']))


@register_resource('/exchange/activity', '/exchange/activity/<string:window>')
class ExchangeActivityResource(Resource):

    @auth_required
    def get(self, window: str = None):
        q = parse_time_window_query(window or 'today')
        q['exchange_id'] = g.user['exchange_id']
        return list(g.db.stock_day_activity.find(q))


@register_resource('/exchange/stocks', '/exchange/stocks/<string:stock_id>')
class ExchangeStockResource(Resource):

    @auth_required
    def get(self, stock_id: str = None):
        if stock_id:
            stock = g.db.stocks.find_one(ObjectId(stock_id))
            if not stock:
                abort(404, message='stock does not exist')
            return stock

        return list(g.db.stocks.find({'exchange_id': g.user['exchange_id']}))
