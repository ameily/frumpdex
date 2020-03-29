#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from bson import ObjectId
from pypsi.core import Command, PypsiArgParser, CommandShortCircuit
from pypsi.format import Table, Column

class VoteCommand(Command):

    def __init__(self):
        super().__init__(name='vote', brief='manage votes')
        self.parser = PypsiArgParser()
        subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd', required=True)


        list_cmd = subcmd.add_parser('list', help='list all stocks in an exchange')
        list_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id')

        create_cmd = subcmd.add_parser('new', help='create new stock')
        create_cmd.add_argument('name', action='store', help='stock name')
        create_cmd.add_argument('-e', '--exchange-id', action='store', help='exchange id',
                                required=True)
        create_cmd.add_argument('-v', '--value', action='store', type=int, default=1000,
                                help='initial stock value')

    def run(self, shell, args):
        try:
            args = self.parser.parse_args(args)
        except CommandShortCircuit as err:
            return err.code

        if args.subcmd == 'list':
            return self.print_stocks(shell, args.exchange_id)

        if args.subcmd == 'new':
            return self.create_stock(shell, args.exchange_id, args.name, args.value)

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_stocks(self, shell, exchange_id: str = None):
        if exchange_id:
            columns = [Column('Id'), Column('Name'), Column('Value')]
            cursor = shell.ctx.db.stocks.find({'exchange_id': ObjectId(exchange_id)})
        else:
            columns = [Column('Id'), Column('Exchange Id'), Column('Name'), Column('Value')]
            cursor = shell.ctx.db.stocks.find()

        table = Table(columns, spacing=4)
        for row in cursor:
            if exchange_id:
                table.append(row['_id'], row['name'], row['value'])
            else:
                table.append(row['_id'], row['exchange_id'], row['name'], row['value'])

        table.write(sys.stdout)
        return 0

    def create_stock(self, shell, exchange_id: str, name: str, value: int):
        stock = shell.ctx.db.create_stock(exchange_id, name, value)
        print('created new stock successfully')
        print()
        print('Id:   ', stock['_id'])
        print('Name: ', stock['name'])
        print('Value:', stock['value'])
        return 0
