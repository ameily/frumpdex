from datetime import datetime
from typing import Union, Any
import arrow
from cincoconfig import Schema, StringField, Field, IntField, ListField, DictField, VirtualField
from cincoconfig.abc import BaseConfig
from bson import ObjectId


class ObjectIdField(Field):

    def _validate(self, cfg: BaseConfig, value: Union[ObjectId, str]) -> ObjectId:
        if isinstance(value, ObjectId):
            return value
        return ObjectId(value)


class DatetimeField(Field):

    def to_basic(self, cfg: BaseConfig, value: datetime) -> datetime:
        return value

    def to_python(self, cfg: BaseConfig, value: Any) -> arrow.Arrow:
        if isinstance(value, str):
            return arrow.get(value).datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, arrow.Arrow):
            return value.datetime
        raise TypeError(f'invalid datetime: {value}')


def stock_statistics_base_doc():
    return {
        'ups': 0,
        'downs': 0,
        'rating': 0
    }


gitlab_activity_schema = Schema(dynamic=True)
gitlab_activity_schema.total = IntField(default=0, min=0)
gitlab_activity_schema.pushed_to = IntField(default=0, min=0)
gitlab_activity_schema.deleted = IntField(default=0, min=0)
gitlab_activity_schema.closed = IntField(default=0, min=0)
gitlab_activity_schema.opened = IntField(default=0, min=0)
gitlab_activity_schema.pushed_new = IntField(default=0, min=0)
gitlab_activity_schema.commented_on = IntField(default=0, min=0)

stock_schema = Schema()
stock_schema._id = ObjectIdField()
stock_schema.exchange_id = ObjectIdField(required=True)
stock_schema.symbol = StringField(required=True)
stock_schema.ups = IntField(default=0, min=0)
stock_schema.downs = IntField(default=0, min=0)
stock_schema.rating = IntField(default=0)
stock_schema.up_labels = DictField(default=dict)
stock_schema.down_labels = DictField(default=dict)
stock_schema.gitlab = gitlab_activity_schema

exchange_schema = Schema()
exchange_schema._id = ObjectIdField()
exchange_schema.name = StringField(required=True)

user_schema = Schema()
user_schema._id = ObjectIdField()
user_schema.exchange_id = ObjectIdField(required=True)
user_schema.name = StringField(required=True)
user_schema.token = StringField(required=True)

vote_label = Schema()
vote_label._id = ObjectIdField()
vote_label.name = StringField(required=True)
vote_label.symbol = StringField(required=True)

vote_schema = Schema()
vote_schema._id = ObjectIdField()
vote_schema.stock_id = ObjectIdField(required=True)
vote_schema.user_id = ObjectIdField(required=True)
vote_schema.exchange_id = ObjectIdField(required=True)
vote_schema.comment = StringField(required=True)
vote_schema.rating = IntField(min=-5, max=5, default=0)
vote_schema.labels = ListField(StringField(), default=lambda: [])
vote_schema.date = DatetimeField(required=True)

@vote_schema.instance_method('get_increment_doc')
def vote_get_inc_doc(vote: 'Vote'):
    label_key = 'up_labels' if vote.rating > 0 else 'down_labels'
    inc = {
        'ups': 1 if vote.rating > 0 else 0,
        'downs': 1 if vote.rating < 0 else 0,
        'rating': vote.rating,
    }
    inc.update({f'{label_key}.{label}': 1 for label in vote.labels})
    return inc

stock_day_activity_schema = Schema()
stock_day_activity_schema._id = ObjectIdField()
stock_day_activity_schema.exchange_id = ObjectIdField(required=True)
stock_day_activity_schema.symbol = StringField(required=True)
stock_day_activity_schema.ups = IntField(default=0, min=0)
stock_day_activity_schema.downs = IntField(default=0, min=0)
stock_day_activity_schema.rating = IntField(default=0)
stock_day_activity_schema.date = DatetimeField(required=True)
stock_day_activity_schema.up_labels = DictField(default=dict)
stock_day_activity_schema.down_labels = DictField(default=dict)
stock_day_activity_schema.gitlab = gitlab_activity_schema

Stock = stock_schema.make_type('Stock')
GitlabActivity = gitlab_activity_schema.make_type('GitlabActivity')
Exchange = exchange_schema.make_type('Exchange')
User = user_schema.make_type('User')
VoteLabel = vote_label.make_type('VoteLabel')
Vote = vote_schema.make_type('Vote')
StockDayActivity = stock_day_activity_schema.make_type('StockDayActivity')
