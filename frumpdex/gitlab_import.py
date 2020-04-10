#!/usr/bin/env python3
from .db import FrumpdexDatabase

import gitlab

from datetime import datetime
from datetime import timedelta

class GitlabActivityReader:
    def __init__(self, uri, token):
        self._gl = gitlab.Gitlab(uri, private_token=token, api_version=4)

    def activity(self, username):
        user = self._gl.users.list(username=username)[0]

        # We have to query for "after" yesterday and "before" tomorrow
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        events = user.events.list(after=yesterday, before=tomorrow)
        activity = {"total": len(events)}

        for event in events:
            event.action_name = event.action_name.replace(' ', '_')
            activity[event.action_name] = activity.get(
                event.action_name, 0) + 1

        return activity


def import_data(mongo_uri, gitlab_uri, gitlab_token):
    # Connect Mongo
    db = FrumpdexDatabase.instance()
    db.connect(mongo_uri)

    # Connect Gitlab
    gl = GitlabActivityReader(gitlab_uri, gitlab_token)

    for stock in db.stocks.find():
        activity = gl.activity(stock['symbol'])
        db.update_gitlab_activity(stock['_id'], activity)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mongo-uri', help='MongoDB URI', action='store', default='mongodb://localhost:27017')
    parser.add_argument('-u', '--gitlab-uri', help='Gitlab URI', action='store')
    parser.add_argument('-t', '--token', help='API token', action='store')
    args = parser.parse_args()

    import_data(args.mongo_uri, args.gitlab_uri, args.token)

