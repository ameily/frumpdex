#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from flask import g
from flask_restful import Resource, abort
from bson import ObjectId

from .lib import register_resource


@register_resource('/vote-labels')
class VoteLabelsResource(Resource):

    def get(self):
        return list(g.db.vote_labels.find())
