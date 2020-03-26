#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column

class ExchangeCommand(Command):

    def __init__(self):
        super().__init__(name='exchange', brief='manage exchanges')
        self.parser = PypsiArgParser()
        subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd')

        subcmd.add_parser('list', help='list all exchanges')

        create_cmd = subcmd.add_parser('new', help='create new exchange')
        create_cmd.add_argument('name', action='store', help='exchange name')

    def run(self, shell, args):
        try:
            args = self.parser.parse_args(args)
        except CommandShortCircuit as err:
            return err.code

        if args.subcmd == 'list':
            return self.print_exchanges(shell)

        if args.subcmd == 'new':
            return self.create_exchange(shell, args)

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_exchanges(self, shell):
        table = Table([Column('Id'), Column('Name')], spacing=4)
        for row in shell.ctx.db.exchanges.find():
            table.append(row['_id'], row['name'])
        table.write(sys.stdout)
        return 0

    def create_exchange(self, shell, args):
        exchange = shell.ctx.db.create_exchange(args.name)
        print('created new exchange successfully')
        print()
        print('Id:  ', exchange['_id'])
        print('Name:', exchange['name'])
        return 0
