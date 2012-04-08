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

from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Quit, restart, or reload components from the bot. Only the owners can
    run this command."""
    name = "quit"

    def check(self, data):
        commands = ["quit", "restart", "reload"]
        return data.is_command and data.command in commands

    def process(self, data):
        if data.host not in self.config.irc["permissions"]["owners"]:
            msg = "you must be a bot owner to use this command."
            self.connection.reply(data, msg)
            return
        if data.command == "quit":
            self.do_quit(data)
        elif data.command == "restart":
            self.do_restart(data)
        else:
            self.do_reload(data)

    def do_quit(self, data):
        nick = self.config.irc.frontend["nick"]
        if not data.args or data.args[0].lower() != nick.lower():
            self.connection.reply(data, "to confirm this action, the first argument must be my nickname.")
            return
        if data.args[1:]:
            msg = " ".join(data.args[1:])
            self.bot.stop("Stopped by {0}: {1}".format(data.nick, msg))
        else:
            self.bot.stop("Stopped by {0}".format(data.nick))

    def do_restart(self, data):
        self.logger.info("Restarting bot per owner request")
        if data.args:
            msg = " ".join(data.args)
            self.bot.restart("Restarted by {0}: {1}".format(data.nick, msg))
        else:
            self.bot.restart("Restarted by {0}".format(data.nick))

    def do_reload(self, data):
        self.logger.info("Reloading IRC commands and bot tasks")
        self.bot.commands.load()
        self.bot.tasks.load()
        self.connection.reply(data, "IRC commands and bot tasks reloaded.")
