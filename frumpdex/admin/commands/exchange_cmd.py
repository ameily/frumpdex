#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from bson import ObjectId
from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column
from pypsi.completers import command_completer

class ExchangeCommand(Command):

    def __init__(self):
        super().__init__(name='exchange', brief='manage exchanges')
        self.parser = PypsiArgParser()
        self.subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd')

        self.subcmd.add_parser('list', help='list all exchanges')

        create_cmd = self.subcmd.add_parser('new', help='create new exchange')
        create_cmd.add_argument('-s', '--select', action='store_true',
                                help='select the exchange after creating it')
        create_cmd.add_argument('name', action='store', help='exchange name')

        select_cmd = self.subcmd.add_parser('select', help='select an active exhcnage')
        select_cmd.add_argument('id', help='exchange id')

        deselect_cmd = self.subcmd.add_parser('deselect', help='deselect active exchange')

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
            return self.print_exchanges(shell)

        if args.subcmd == 'new':
            return self.create_exchange(shell, args.name, args.select)

        if args.subcmd == 'select':
            return self.select_exchange(shell, args.id)

        if args.subcmd == 'deselect':
            shell.select_exchange(None)
            return 0

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_exchanges(self, shell):
        table = Table([Column('Id'), Column('Name')], spacing=4)
        for row in shell.ctx.db.exchanges.find():
            table.append(row['_id'], row['name'])
        table.write(sys.stdout)
        return 0

    def create_exchange(self, shell, name: str, select: bool):
        exchange = shell.ctx.db.create_exchange(name)
        print('created new exchange successfully')
        print()
        print('Id:  ', exchange['_id'])
        print('Name:', exchange['name'])

        if select:
            shell.select_exchange(exchange)

        return 0

    def select_exchange(self, shell, exchange_id: str):
        exchange = shell.ctx.db.exchanges.find_one(ObjectId(exchange_id))
        if not exchange:
            self.error(shell, f'exhcnage does not exist: {exchange_id}')
            return 1

        shell.select_exchange(exchange)
        return 0

