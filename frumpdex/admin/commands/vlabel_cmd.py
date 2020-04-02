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

class VoteLabelCommand(Command):

    def __init__(self):
        super().__init__(name='vlabel', brief='manage vote labels')
        self.parser = PypsiArgParser()
        self.subcmd = self.parser.add_subparsers(help='subcmd', dest='subcmd', required=True)


        self.subcmd.add_parser('list', help='list all vote labels')

        create_cmd = self.subcmd.add_parser('new', help='create new vote label')
        create_cmd.add_argument('name', action='store', help='label name')

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
            return self.print_vote_labels(shell)

        if args.subcmd == 'new':
            return self.create_vote_label(shell, args.name)

        self.error(shell, f'unknown sub-command: {args.subcmd}')

    def print_vote_labels(self, shell):
        cursor = shell.ctx.db.vote_labels.find()

        table = Table([Column('Id'), Column('Name'), Column('Symbol')], spacing=4)
        for row in cursor:
            table.append(row['_id'], row['name'], row['symbol'])

        table.write(sys.stdout)
        return 0

    def create_vote_label(self, shell, name: str):
        vlabel = shell.ctx.db.create_vote_label(name)

        print('created new user successfully')
        print()
        print('Id:    ', vlabel['_id'])
        print('Name:  ', vlabel['name'])
        print('Symbol:', vlabel['symbol'])
        return 0
