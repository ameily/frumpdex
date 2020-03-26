#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g
from flask_restful import Resource, abort
from bson import ObjectId
from datetime import datetime, timedelta

from .lib import register_resource


@register_resource('/trades', '/trades/<str:window>')
class ExchangeResource(Resource):

    @property
    def today(self) -> datetime:
        return datetime.utcnow().replace(minute=0, second=0, microsecond=0, hour=0)

    def get(self, window: str = None):
        # TODO properly normalize to utc
        if not window or window == 'today':
            q = {'timestamp': {'$ge': self.today}}
        elif window == 'week':
            today = self.today
            q = {'timestamp': {'$ge': today - timedelta(days=today.weekday())}}
        elif window == 'month':
            today = self.today.replace(minute=0, second=0, microsecond=0, hour=0, day=1)
            q = {'timestamp': {'$ge': today}}
        elif window == 'year':
            today = datetime.utcnow().replace(minute=0, second=0, microsecond=0, hour=0, day=1,
                                              month=1)
            q = {'timestamp': {'$ge': today}}
        elif window:
            q = {}  # TODO handle custom window

        # TODO scope to user's exchange
        return list(g.db.trades.find(q))
