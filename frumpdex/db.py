#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import logging
from typing import List, Union, Any
import threading
import secrets

import pymongo
import pymongo.collection
import pymongo.database
from bson import ObjectId
from slugify import slugify
import arrow

logger = logging.getLogger(__name__)


def midnight(reftime: arrow.Arrow = None) -> arrow.Arrow:
    reftime = reftime or arrow.now()
    return reftime.replace(hour=0, minute=0, second=0, microsecond=0)


class ItemDoesNotExist(Exception):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    def __str__(self) -> str:
        return f'{self.collection_name} does not exist'


DataItemId = Union[str, ObjectId]

class DataItem:
    def __init__(self, obj: dict):
        self.__obj = obj

    def __getattr__(self, name: str) -> Any:
        return self.__obj[name]

    def __setattr__(self, name, value):
        if name.startswith('__'):
            super().__setattr__(name, value)
        else:
            self.__obj[name] = value


class FrumpdexDatabase:
    __instance: 'FrumpdexDatabase' = None

    @classmethod
    def instance(cls) -> 'FrumpdexDatabase':
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.client = None
        self.__trade_lock = threading.Lock()

    def connect(self, uri: str = 'mongodb://localhost:27017') -> None:
        client = pymongo.MongoClient(uri)
        client.server_info()

        self.client = client

    def _create_indexes(self):
        db = self.db
        collection_names = db.collection_names()
        if 'users' not in collection_names:
            logger.info('creating index for users collection')
            users = db.create_collection('users')
            users.create_index('token')

        if 'votes' not in collection_names:
            logger.info('creating index for votes collection')
            votes = db.create_collection('votes')
            votes.create_index('exchange_id')
            votes.create_index('stock_id')
            votes.create_index('user_id')

        if 'stock_day_activity' not in collection_names:
            logger.info('creating index for stock_day_activity collection')
            activity = db.create_collection('stock_day_activity')
            activity.create_index('exchange_id')
            activity.create_index('stock_id')

        if 'stocks' not in collection_names:
            logger.info('creating index for stocks collection')
            stocks = db.create_collection('stocks')
            stocks.create_index('exchange_id')

    @property
    def db(self) -> pymongo.database.Database:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex

    @property
    def users(self) -> pymongo.collection.Collection:
        return self.db.users

    @property
    def votes(self) -> pymongo.collection.Collection:
        return self.db.votes

    @property
    def exchanges(self) -> pymongo.collection.Collection:
        return self.db.exchanges

    @property
    def stocks(self) -> pymongo.collection.Collection:
        return self.db.stocks

    @property
    def stock_day_activity(self) -> pymongo.collection.Collection:
        return self.db.stock_day_activity

    def vote(self, stock_id: DataItemId, token: str, direction: str, message: str = None) -> dict:
        stock_id = ObjectId(stock_id)
        stock = self.stocks.find_one(stock_id)

        if direction in ('up', '1', '+1'):
            inc_doc = {
                'ups': 1,
                'downs': 0,
                'votes': 1
            }
        elif direction in ('down', '-1'):
            inc_doc = {
                'downs': 1,
                'ups': 0,
                'votes': -1
            }
        else:
            raise TypeError(f'invalid vote: {direction} -- must be either "up" or "down"')

        if not stock:
            raise ItemDoesNotExist('stock')

        user = self.login(token)
        if not user:
            raise ItemDoesNotExist('user')

        if user['exchange_id'] != stock['exchange_id']:
            raise ItemDoesNotExist('user')

        today = midnight().datetime

        vote = {
            '_id': ObjectId(),
            'stock_id': stock_id,
            'user_id': user['_id'],
            'exchange_id': user['exchange_id'],
            'vote': 1 if direction == 'up' else -1,
            'message': message or '',
            'date': today
        }

        logger.info(f'user {user["name"]} is voting {direction} stock {stock["name"]}')
        self.votes.insert_one(vote)

        self.stock_day_activity.update_one({
            'stock_id': stock['_id'],
            'exchange_id': stock['exchange_id'],
            'date': today
        }, {
            '$inc': inc_doc
        }, upsert=True)

        self.stocks.update_one({'_id': stock['_id']}, {
            '$inc': inc_doc
        })

        return vote

    def create_exchange(self, name: str) -> ObjectId:
        exchange = {'name': name, '_id': ObjectId()}
        self.exchanges.insert_one(exchange)
        logger.info(f'created exchange {name} -> {exchange["_id"]}')
        return exchange

    def create_user(self, exchange_id: DataItemId, name: str) -> dict:
        exchange = self.exchanges.find_one(ObjectId(exchange_id))
        if not exchange:
            raise ItemDoesNotExist('exchange')

        token = secrets.token_hex(16)
        user = {
            'exchange_id': exchange['_id'],
            'name': name,
            'token': token,
            '_id': ObjectId()
        }
        self.users.insert_one(user)

        logger.info(f'created user {name} @ {exchange["name"]} -> {user["_id"]}')

        return user

    def create_stock(self, exchange_id: DataItemId, name: str, symbol: str = None) -> dict:
        exchange = self.exchanges.find_one(ObjectId(exchange_id))
        if not exchange:
            raise ItemDoesNotExist('exchange')

        if not symbol:
            symbol = slugify(name)

        stock = {
            'exchange_id': ObjectId(exchange_id),
            'name': name,
            'symbol': symbol,
            'ups': 0,
            'downs': 0,
            'votes': 0,
            '_id': ObjectId()
        }
        self.stocks.insert_one(stock)

        logger.info(f'created stock {name} @ {exchange["name"]} -> {stock["_id"]}')
        return stock

    def login(self, token: str) -> dict:
        user = self.users.find_one({'token': token})
        if user:
            logger.info(f'user authenticated: {user["name"]} @ exchange id {user["exchange_id"]}')
        else:
            logger.error(f'user token incorrect: {token}')

        return user
