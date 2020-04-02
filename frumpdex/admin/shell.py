#
# Copyright (c) 2020, Adam Meily
# All rights reserved.
#
import sys

from pypsi.shell import Shell
from pypsi.commands.exit import ExitCommand
from pypsi.commands.echo import EchoCommand
from pypsi.commands.help import HelpCommand
from pypsi.commands.include import IncludeCommand
from pypsi.commands.macro import MacroCommand
from pypsi.commands.pwd import PwdCommand
from pypsi.commands.system import SystemCommand
from pypsi.plugins.comment import CommentPlugin
from pypsi.plugins.variable import VariablePlugin
from pypsi.plugins.history import HistoryPlugin
from pypsi.plugins.multiline import MultilinePlugin
from pypsi.plugins.block import BlockPlugin
from pypsi.plugins.hexcode import HexCodePlugin
from pypsi.ansi import AnsiCodes

from . import commands
from ..db import FrumpdexDatabase

class AdminShell(Shell):
    exchange_cmd = commands.ExchangeCommand()
    stock_cmd = commands.StockCommand()
    user_cmd = commands.UserCommand()
    vlabel_cmd = commands.VoteLabelCommand()

    exit_cmd = ExitCommand()
    echo_cmd = EchoCommand()
    help_cmd = HelpCommand()
    include_cmd = IncludeCommand()
    macro_cmd = MacroCommand()
    pwd_cmd = PwdCommand()
    var_plugin = VariablePlugin(case_sensitive=False, env=False)
    comment_plugin = CommentPlugin()
    history_plugin = HistoryPlugin()
    ml_plugin = MultilinePlugin()
    block_plugin = BlockPlugin()
    hexcode_plugin = HexCodePlugin()
    system_cmd = SystemCommand(use_shell=(sys.platform == 'win32'))

    def on_cmdloop_begin(self):
        self.select_exchange(None)
        self.fallback_cmd = self.system_cmd
        self.ctx.db = FrumpdexDatabase()
        self.ctx.db.connect()

    def select_exchange(self, exchange: dict):
        self.ctx.exchange = exchange
        prompt = (f'{AnsiCodes.gray.prompt()}[$time]{AnsiCodes.reset.prompt()} '
                  f'{AnsiCodes.cyan.prompt()}frumpdex{AnsiCodes.reset.prompt()}')

        if exchange:
            prompt += (f'{AnsiCodes.yellow.prompt()}[{exchange["name"]}]'
                       f'{AnsiCodes.reset.prompt()}')

        prompt += f' {AnsiCodes.green.prompt()})>{AnsiCodes.reset.prompt()} '
        self.prompt = prompt
