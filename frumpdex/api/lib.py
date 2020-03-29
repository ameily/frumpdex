#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import os
import importlib
from typing import List, Union, Callable, Type, Tuple
from datetime import datetime, timedelta, date
from bson import ObjectId
import arrow

from flask import request, session, g
from flask_restful import abort, Resource

from ..db import midnight


RESOURCES = []

def register_resource(*endpoints):
    def inner(resource_cls):
        RESOURCES.append((resource_cls, endpoints))
        return resource_cls
    return inner


def get_registered_resources() -> List[Tuple[Type[Resource], List[str]]]:
    for filename in os.listdir(os.path.dirname(__file__)):
        modname, ext = os.path.splitext(filename)
        if ext == '.py' and modname not in ('__init__', 'lib'):
            modpath = f'{__package__}.{modname}'
            importlib.import_module(modpath)
    return list(RESOURCES)


def parse_time_window_query(window: str) -> dict:
    today_midnight = midnight()
    if not window or window == 'today':
        q = {'date': {'$gte': today_midnight.datetime}}
    elif window == 'week':
        q = {'date': {'$gte': today_midnight - timedelta(days=today_midnight.weekday())}}
    elif window == 'month':
        # today = today.replace(minute=0, second=0, microsecond=0, hour=0, day=1)
        q = {'date': {'$gte': today_midnight.replace(day=1).datetime}}
    elif window == 'year':
        q = {'date': {'$gte': today_midnight.replace(month=1, day=1).datetime}}
    elif window == 'lifetime':
        q = {}
    elif window:
        q = {}  # TODO handle custom window

    print('QUERY:', q)
    return q


def auth_required(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        if not g.user:
            abort(403, message='api token required')
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def serialize_extra_types(value, default=None):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if default:
        return default(value)
    raise TypeError(f'unserializable type: {type(value)}')
