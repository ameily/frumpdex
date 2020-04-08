#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
from cincoconfig import *  # pylint: disable=unused-wildcard-import

schema = Schema()
schema.mode = ApplicationModeField(default='production', modes=['debug', 'production'])

schema.http.port = PortField(default=5000, required=True)
schema.http.address = IPv4AddressField(default='127.0.0.1', required=True)
schema.http.cors.allowed_origins = ListField(StringField())

schema.gitlab.private_token = StringField()
schema.gitlab.url = UrlField()

schema.logfile = FilenameField()
schema.silent = BoolField(default=False)

schema.mongodb.url = UrlField(default='mongodb://localhost:27017', required=True)

config = schema()
