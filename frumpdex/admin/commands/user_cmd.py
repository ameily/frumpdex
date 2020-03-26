#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from bson import ObjectId
from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column

from frumpdex.db import ItemDoesNotExist

class UserCommand(Command):

    def __init__(self):
        super().__init__(name='user', brief='manage users')
        self.parser = PypsiArgParser()
        subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd', required=True)


        list_cmd = subcmd.add_parser('list', help='list all users in an exchange')
        list_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

        create_cmd = subcmd.add_parser('new', help='create new user')
        create_cmd.add_argument('name', action='store', help='user name')
        create_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id',
                                required=True)

        describe_cmd = subcmd.add_parser('describe', help='describe user details')
        describe_cmd.add_argument('-u', '--user-id', help='user id', action='store', required=True)

    def run(self, shell, args):
        try:
            args = self.parser.parse_args(args)
        except CommandShortCircuit as err:
            return err.code

        if args.subcmd == 'list':
            return self.print_users(shell, args.exchange_id)

        if args.subcmd == 'new':
            return self.create_user(shell, args.exchange_id, args.name)

        if args.subcmd == 'describe':
            return self.describe_user(shell, args.user_id)

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_users(self, shell, exchange_id: str = None):
        if exchange_id:
            columns = [Column('Id'), Column('Name')]
            cursor = shell.ctx.db.users.find({'exchange_id': ObjectId(exchange_id)})
        else:
            columns = [Column('Id'), Column('Exchange Id'), Column('Name')]
            cursor = shell.ctx.db.users.find()

        table = Table(columns, spacing=4)
        for row in cursor:
            if exchange_id:
                table.append(row['_id'], row['name'])
            else:
                table.append(row['_id'], row['exchange_id'], row['name'])

        table.write(sys.stdout)
        return 0

    def create_user(self, shell, exchange_id: str, name: str):
        try:
            user = shell.ctx.db.create_user(exchange_id, name)
        except ItemDoesNotExist as err:
            self.error(shell, f'failed to create user: {err} - {exchange_id}')
            return -1

        print('created new user successfully')
        print()
        print('Id:   ', user['_id'])
        print('Name: ', user['name'])
        print('Token:', user['token'])
        return 0

    def describe_user(self, shell, user_id: str):
        user = shell.ctx.db.users.find_one(ObjectId(user_id))
        if not user:
            self.error(shell, 'user does not exist')
            return 1

        print('Id:         ', user['_id'])
        print('Exchange Id:', user['exchange_id'])
        print('Name:       ', user['name'])
        print('Token:      ', user['token'])
        return 0
