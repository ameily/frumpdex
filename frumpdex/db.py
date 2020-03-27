#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from typing import List, Union, Any
import threading
import secrets
from datetime import datetime

import pymongo
import pymongo.collection
from bson import ObjectId
import arrow


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

    def connect(self, hostname: str = 'localhost', port: int = 27017) -> None:
        client = pymongo.MongoClient(hostname, port)
        client.server_info()

        self.client = client

    @property
    def users(self) -> pymongo.collection.Collection:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex.users

    @property
    def votes(self) -> pymongo.collection.Collection:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex.votes

    @property
    def exchanges(self) -> pymongo.collection.Collection:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex.exchanges

    @property
    def stocks(self) -> pymongo.collection.Collection:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex.stocks

    @property
    def stock_day_activity(self) -> pymongo.collection.Collection:
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex.stock_day_activity

    def vote(self, stock_id: DataItemId, token: str, direction: str, message: str = None) -> dict:
        stock_id = ObjectId(stock_id)
        stock = self.stocks.find_one(stock_id)

        if direction in ('up', '1', '+1'):
            inc_doc = {
                'ups': 1,
                'votes': 1
            }
        elif direction in ('down', '-1'):
            inc_doc = {
                'downs': 1,
                'votes': -1
            }
        else:
            raise TypeError(f'invalid vote: {direction} -- must be either "up" or "down"')

        if not stock:
            raise ItemDoesNotExist('stock')

        user = self.login(stock['exchange_id'], token)
        if not user:
            raise ItemDoesNotExist('user')

        if user['exchange_id'] != stock['exchange_id']:
            raise ItemDoesNotExist('user')

        vote = {
            '_id': ObjectId(),
            'stock_id': stock_id,
            'user_id': user['_id'],
            'exchange_id': user['exchange_id'],
            'vote': 1 if direction == 'up' else -1,
            'message': message or ''
        }
        self.votes.insert_one(vote)

        self.stock_day_activity.upsert_one({
            'stock_id': stock['_id'],
            'exchange_id': stock['exchange_id'],
            'date': arrow.now().date()
        }, {
            '$inc': inc_doc
        })

        return vote

    def create_exchange(self, name: str) -> ObjectId:
        exchange = {'name': name, '_id': ObjectId()}
        self.exchanges.insert_one(exchange)
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

        return user

    def create_stock(self, exchange_id: DataItemId, name: str, value: int = 0) -> dict:
        stock = {
            'exchange_id': ObjectId(exchange_id),
            'name': name,
            'value': value,
            '_id': ObjectId()
        }
        self.stocks.insert_one(stock)
        return stock

    def login(self, exchange_id: DataItemId, token: str) -> dict:
        return self.users.find_one({'exchange_id': ObjectId(exchange_id), 'token': token})
