# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

import re

from earwigbot.commands import BaseCommand
from earwigbot.irc import Data

class Command(BaseCommand):
    """Displays help information."""
    name = "help"

    def check(self, data):
        if data.is_command:
            if data.command == "help":
                return True
            if not data.command and data.trigger == data.my_nick:
                return True
        return False

    def process(self, data):
        if not data.command:
            self.do_hello(data)
        elif data.args:
            self.do_command_help(data)
        else:
            self.do_main_help(data)

    def do_main_help(self, data):
        """Give the user a general help message with a list of all commands."""
        msg = "Hi, I'm a bot! I have {0} commands loaded: {1}. You can get help for any command with '!help <command>'."
        cmnds = sorted(self.bot.commands)
        msg = msg.format(len(cmnds), ', '.join(cmnds))
        self.reply(data, msg)

    def do_command_help(self, data):
        """Give the user help for a specific command."""
        command = data.args[0]

        # Create a dummy message to test which commands pick up the user's
        # input:
        dummy = Data(":foo!bar@example.com PRIVMSG #channel :msg!".split())
        dummy.command = command.lower()
        dummy.is_command = True

        for cmnd_name in self.bot.commands:
            cmnd = self.bot.commands.get(cmnd_name)
            if not cmnd.check(dummy):
                continue
            if cmnd.__doc__:
                doc = cmnd.__doc__.replace("\n", "")
                doc = re.sub("\s\s+", " ", doc)
                msg = "help for command \x0303{0}\x0301: \"{1}\""
                self.reply(data, msg.format(command, doc))
                return
            break

        msg = "sorry, no help for \x0303{0}\x0301.".format(command)
        self.reply(data, msg)

    def do_hello(self, data):
        self.say(data.chan, "Yes, {0}?".format(data.nick))
