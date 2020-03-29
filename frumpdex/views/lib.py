import os
import importlib
from typing import List
from flask import g, abort, Blueprint, redirect, url_for, request


def auth_required(func):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for('auth.login', next=request.path))
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def get_blueprints() -> List[Blueprint]:
    ret = []
    for filename in os.listdir(os.path.dirname(__file__)):
        modname, ext = os.path.splitext(filename)
        if ext == '.py' and modname not in ('__init__', 'lib'):
            modpath = f'{__package__}.{modname}'
            module = importlib.import_module(modpath)
            blueprint = getattr(module, 'blueprint', None)
            if blueprint:
                ret.append(blueprint)
    return ret
