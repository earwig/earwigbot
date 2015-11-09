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

from earwigbot.commands import Command

class Quit(Command):
    """Quit, restart, or reload components from the bot. Only the owners can
    run this command."""
    name = "quit"
    commands = ["quit", "restart", "reload"]

    def process(self, data):
        if not self.config.irc["permissions"].is_owner(data):
            self.reply(data, "You must be a bot owner to use this command.")
            return
        if data.command == "quit":
            self.do_quit(data)
        elif data.command == "restart":
            self.do_restart(data)
        else:
            self.do_reload(data)

    def do_quit(self, data):
        args = data.args
        if data.trigger == data.my_nick:
            reason = " ".join(args)
        else:
            if not args or args[0].lower() != data.my_nick:
                self.reply(data, "To confirm this action, the first argument must be my name.")
                return
            reason = " ".join(args[1:])

        if reason:
            self.bot.stop("Stopped by {0}: {1}".format(data.nick, reason))
        else:
            self.bot.stop("Stopped by {0}".format(data.nick))

    def do_restart(self, data):
        if data.args:
            msg = " ".join(data.args)
            self.bot.restart("Restarted by {0}: {1}".format(data.nick, msg))
        else:
            self.bot.restart("Restarted by {0}".format(data.nick))

    def do_reload(self, data):
        self.logger.info("{0} requested command/task reload".format(data.nick))
        self.bot.commands.load()
        self.bot.tasks.load()
        self.reply(data, "IRC commands and bot tasks reloaded.")
