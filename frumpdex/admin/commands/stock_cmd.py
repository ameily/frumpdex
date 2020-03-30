#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from bson import ObjectId
from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column
from pypsi.ansi import AnsiCodes
from pypsi.completers import command_completer


class StockCommand(Command):

    def __init__(self):
        super().__init__(name='stock', brief='manage stocks')
        self.parser = PypsiArgParser()
        self.subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd', required=True)


        list_cmd = self.subcmd.add_parser('list', help='list all stocks in an exchange')
        list_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

        create_cmd = self.subcmd.add_parser('new', help='create new stock')
        create_cmd.add_argument('name', action='store', help='stock name')
        create_cmd.add_argument('-s', '--symbol', action='store', help='stock symbol')
        create_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

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
            return self.print_stocks(shell, exchange_id)

        if args.subcmd == 'new':
            exchange_id = args.exchange_id
            if not exchange_id and shell.ctx.exchange:
                exchange_id = shell.ctx.exchange['_id']
            elif not exchange_id:
                self.error(shell, 'missing required argument -e/--exchange-id')
                return 1

            return self.create_stock(shell, exchange_id, args.name, args.symbol)

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_stocks(self, shell, exchange_id: str = None):
        if exchange_id:
            columns = [Column('Id'), Column('Name'), Column('Ups'), Column('Downs')]
            cursor = shell.ctx.db.stocks.find({'exchange_id': ObjectId(exchange_id)})
        else:
            columns = [Column('Id'), Column('Exchange Id'), Column('Name'), Column('Ups'),
                       Column('Downs')]
            cursor = shell.ctx.db.stocks.find()

        table = Table(columns, spacing=4)
        for row in cursor:
            if exchange_id:
                table.append(row['_id'], row['name'], row['ups'], row['downs'])
            else:
                table.append(row['_id'], row['exchange_id'], row['name'], row['ups'], row['downs'])

        table.write(sys.stdout)
        return 0

    def create_stock(self, shell, exchange_id: str, name: str, symbol: str):
        stock = shell.ctx.db.create_stock(exchange_id, name, symbol)
        print('created new stock successfully')
        print()
        print('Id:    ', stock['_id'])
        print('Name:  ', stock['name'])
        print('Symbol:', stock['symbol'])
        return 0
