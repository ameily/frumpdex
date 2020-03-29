#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g, request
from flask_restful import Resource, abort
from bson import ObjectId

from .lib import register_resource, parse_time_window_query, auth_required


@register_resource('/votes', '/votes/<string:window>',)
class VoteResource(Resource):

    @auth_required
    def get(self, window: str = None, stock_id: str = None):
        if not g.user:
            abort(403, message='api token required')

        q = parse_time_window_query(window or 'today')
        if stock_id:
            q['stock_id'] = ObjectId(stock_id)

        q['exchange_id'] = g.user['exchange_id']

        # TODO scope to user's exchange
        return list(g.db.votes.find(q))


@register_resource('/stocks/<string:stock_id>/votes', '/stocks/<string:stock_id>/<string:window>')
class VoteStockResource(VoteResource):

    def get(self, stock_id: str, window: str = None):
        super().get(window, stock_id)

    @auth_required
    def post(self, stock_id: str):
        stock = g.db.stocks.find_one(ObjectId(stock_id))
        if not stock:
            abort(404, message='stock does not exist')

        if stock['exchange_id'] != g.user['exchange_id']:
            abort(404, message='stock does not exist')

        vote = g.db.vote(stock_id, g.user['token'], request.form['direction'],
                         request.form['message'])

        g.socketio.emit('vote', vote, room=f'exchange.{stock["exchange_id"]}')

        return vote


