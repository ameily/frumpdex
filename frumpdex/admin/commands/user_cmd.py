#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from bson import ObjectId
from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column
from pypsi.completers import command_completer

from frumpdex.db import ItemDoesNotExist

class UserCommand(Command):

    def __init__(self):
        super().__init__(name='user', brief='manage users')
        self.parser = PypsiArgParser()
        self.subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd', required=True)


        list_cmd = self.subcmd.add_parser('list', help='list all users in an exchange')
        list_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

        create_cmd = self.subcmd.add_parser('new', help='create new user')
        create_cmd.add_argument('name', action='store', help='user name')
        create_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

        describe_cmd = self.subcmd.add_parser('describe', help='describe user details')
        describe_cmd.add_argument('id', help='user id')

    def complete(self, shell, args, prefix):
        if len(args) == 1 and args[0].startswith('-'):
            completions = command_completer(self.parser, shell, args, prefix)
        else:
            completions = command_completer(self.subcmd, shell, args, prefix)
        return completions

    def run(self, shell, args):
        try:
            args = self.parser.parse_args(args)
        except CommandShortCircuit as err:
            return err.code

        if args.subcmd == 'list':
            exchange_id = args.exchange_id
            if not exchange_id and shell.ctx.exchange:
                exchange_id = shell.ctx.exchange['_id']
            return self.print_users(shell, exchange_id)

        if args.subcmd == 'new':
            exchange_id = args.exchange_id
            if not exchange_id and shell.ctx.exchange:
                exchange_id = shell.ctx.exchange['_id']
            elif not exchange_id:
                self.error(shell, 'missing required argument -e/--exchange-id')
                return 1

            return self.create_user(shell, exchange_id, args.name)

        if args.subcmd == 'describe':
            return self.describe_user(shell, args.id)

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
