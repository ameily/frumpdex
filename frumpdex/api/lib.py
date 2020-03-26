#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from typing import List, Union

from flask import request, session
from flask_restful import abort


RESOURCES = []

def register_resource(*endpoints):
    def inner(resource_cls):
        RESOURCES.append((resource_cls, endpoints))
        return resource_cls
    return inner


def get_registered_resources():
    return list(RESOURCES)
