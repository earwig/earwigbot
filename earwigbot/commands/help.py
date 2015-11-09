# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from platform import python_version
import re

from earwigbot import __version__
from earwigbot.commands import Command

class Help(Command):
    """Displays information about the bot."""
    name = "help"
    commands = ["help", "version"]

    def check(self, data):
        if data.is_command:
            if data.command in self.commands:
                return True
            if not data.command and data.trigger == data.my_nick:
                return True
        return False

    def process(self, data):
        if not data.command:
            self.do_hello(data)
        elif data.command == "version":
            self.do_version(data)
        elif data.args:
            self.do_command_help(data)
        else:
            self.do_main_help(data)

    def do_main_help(self, data):
        """Give the user a general help message with a list of all commands."""
        msg = "Hi, I'm a bot! I have {0} commands loaded: {1}. You can get help for any command with '!help <command>'."
        cmnds = sorted([cmnd.name for cmnd in self.bot.commands])
        msg = msg.format(len(cmnds), ', '.join(cmnds))
        self.reply(data, msg)

    def do_command_help(self, data):
        """Give the user help for a specific command."""
        target = data.args[0]

        for command in self.bot.commands:
            if command.name == target or target in command.commands:
                if command.__doc__:
                    doc = command.__doc__.replace("\n", "")
                    doc = re.sub("\s\s+", " ", doc)
                    msg = 'Help for command \x0303{0}\x0F: "{1}"'
                    self.reply(data, msg.format(target, doc))
                    return

        msg = "Sorry, no help for \x0303{0}\x0F.".format(target)
        self.reply(data, msg)

    def do_hello(self, data):
        self.say(data.chan, "Yes, {0}?".format(data.nick))

    def do_version(self, data):
        vers = "EarwigBot v{bot} on Python {python}: https://github.com/earwig/earwigbot"
        self.reply(data, vers.format(bot=__version__, python=python_version()))
