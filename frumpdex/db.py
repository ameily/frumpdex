#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import logging
from typing import List, Union, Any, Optional
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
    '''
    Helper method to return the arrow object representing midnight.

    :param reftime: the day to get midnight, or use ``arrow.now()`` if not specified
    :returns: the arrow of ``reftime`` at midnight
    '''
    reftime = reftime or arrow.now()
    return reftime.replace(hour=0, minute=0, second=0, microsecond=0)


class ItemDoesNotExist(Exception):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    def __str__(self) -> str:
        return f'{self.collection_name} does not exist'


ObjectIdStr = Union[str, ObjectId]


class FrumpdexDatabase:
    '''
    Frumpdex database singleton class.
    '''
    __instance: 'FrumpdexDatabase' = None

    @classmethod
    def instance(cls) -> 'FrumpdexDatabase':
        '''
        :returns: frumpdex database instance
        '''
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.client = None
        self.__trade_lock = threading.Lock()

    def connect(self, uri: str = 'mongodb://localhost:27017') -> None:
        '''
        Connect to a MongoDB server. This method will raise an exception if the connection fails.

        :param uri: mongodb server connection uri
        '''
        client = pymongo.MongoClient(uri)
        client.server_info()

        self.client = client

    def _create_indexes(self) -> None:
        '''
        Create collection indexes.
        '''
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
            votes.create_index('labels')

        if 'stock_day_activity' not in collection_names:
            logger.info('creating index for stock_day_activity collection')
            activity = db.create_collection('stock_day_activity')
            activity.create_index('exchange_id')
            activity.create_index('stock_id')

        if 'stocks' not in collection_names:
            logger.info('creating index for stocks collection')
            stocks = db.create_collection('stocks')
            stocks.create_index('exchange_id')

        if 'vote_labels' not in collection_names:
            logger.info('creating index for vote_labels collection')
            vlabels = db.create_collection('vote_labels')
            vlabels.create_index('symbol')

    @property
    def db(self) -> pymongo.database.Database:
        '''
        :returns: the mongo database of frumpdex
        '''
        if not self.client:
            raise TypeError('database is not connected')
        return self.client.frumpdex

    @property
    def users(self) -> pymongo.collection.Collection:
        '''
        :returns: the users collection
        '''
        return self.db.users

    @property
    def votes(self) -> pymongo.collection.Collection:
        '''
        :returns: the votes collection
        '''
        return self.db.votes

    @property
    def vote_labels(self) -> pymongo.collection.Collection:
        '''
        :returns: the vote_labels collection
        '''
        return self.db.vote_labels

    @property
    def exchanges(self) -> pymongo.collection.Collection:
        '''
        :returns: the exchanges collection
        '''
        return self.db.exchanges

    @property
    def stocks(self) -> pymongo.collection.Collection:
        '''
        :returns: the stocks collection
        '''
        return self.db.stocks

    @property
    def stock_day_activity(self) -> pymongo.collection.Collection:
        '''
        :returns: the stock_day_activity collection
        '''
        return self.db.stock_day_activity

    def vote(self, stock_id: ObjectIdStr, token: str, direction: str, comment: str,
             rating: int = 0, labels: List[str] = None) -> dict:
        '''
        Cast a vote.

        :param stock_id: stock being voted on
        :param token: user API token
        :param direction: the vote direction, either "up" (positive vote) or "down" (negative vote)
        :param comment: vote comment
        :param rating: the vote rating (1 - 5)
        :param labels: the list of label symbols applying to the vote
        :returns: the created vote
        '''
        stock_id = ObjectId(stock_id)
        stock = self.stocks.find_one(stock_id)

        if direction in ('up', '1', '+1'):
            inc_doc = {
                'ups': 1,
                'downs': 0
            }
            if not rating:
                rating = 1
            elif rating < 0:
                rating *= -1

            if rating > 5:
                rating = 5
        elif direction in ('down', '-1'):
            inc_doc = {
                'downs': 1,
                'ups': 0
            }
            if not rating:
                rating = -1
            elif rating > 0:
                rating *= -1

            if rating < -5:
                raitng = -5
        else:
            raise TypeError(f'invalid vote: {direction} -- must be either "up" or "down"')

        inc_doc['rating'] = rating

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
            # 'vote': 1 if direction == 'up' else -1,
            'comment': comment,
            'rating': rating,
            'labels': labels or [],
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

    def create_exchange(self, name: str) -> dict:
        '''
        Create a a new exchange.

        :param name: the exchange name
        :returns: the new exchange
        '''
        exchange = {'name': name, '_id': ObjectId()}
        self.exchanges.insert_one(exchange)
        logger.info(f'created exchange {name} -> {exchange["_id"]}')
        return exchange

    def create_user(self, exchange_id: ObjectIdStr, name: str) -> dict:
        '''
        Create a new user.

        :param exchange_id: exchange id
        :param name: user name
        :returns: the new user
        '''
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

    def create_stock(self, exchange_id: ObjectIdStr, name: str, symbol: str = None) -> dict:
        '''
        Create a new stock.

        :param exchange_id: exchange id
        :param name: stock name
        :param symbol: stock symbol, will be autogenerated if not specified
        :returns: the new stock
        '''
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

    def create_vote_label(self, name: str) -> dict:
        '''
        Create a new vote label.

        :param name: vote label name
        :returns: the new vote label
        '''
        label = {
            '_id': ObjectId(),
            'name': name,
            'symbol': slugify(name)
        }
        self.vote_labels.insert_one(label)
        return label

    def login(self, token: str) -> Optional[dict]:
        '''
        Attempt to authenticate a user based on their API token.

        :returns: the authenticated user from the database if the API token is valid and correct
        '''
        user = self.users.find_one({'token': token})
        if user:
            logger.info(f'user authenticated: {user["name"]} @ exchange id {user["exchange_id"]}')
        else:
            logger.error(f'user token incorrect: {token}')

        return user
