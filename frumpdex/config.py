from cincoconfig import *  # pylint: disable=unused-wildcard-import

schema = Schema()
schema.mode = ApplicationModeField(default='production')

schema.http.port = PortField(default=5000, required=True)
schema.http.address = IPv4AddressField(default='127.0.0.1', required=True)
schema.http.cors_allowed_origins = ListField(StringField())

schema.gitlab.private_token = StringField()
schema.gitlab.url = UrlField()

schema.logfile = FilenameField()

schema.mongodb.url = UrlField(default='mongodb://localhost:27017', required=True)

config = schema()
