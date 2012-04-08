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
    """Restart the bot. Only the owner can do this."""
    name = "restart"

    def check(self, data):
        commands = ["restart", "reload"]
        return data.is_command and data.command in commands

    def process(self, data):
        if data.host not in self.config.irc["permissions"]["owners"]:
            msg = "you must be a bot owner to use this command."
            self.connection.reply(data, msg)
            return

        if data.command == "restart":
            self.logger.info("Restarting bot per owner request")
            if data.args:
                self.bot.restart(" ".join(data.args))
            else:
                self.bot.restart()

        elif data.command == "reload":
            self.logger.info("Reloading IRC commands")
            self.bot.commands.load()
            self.logger.info("Reloading bot tasks")
            self.bot.tasks.load()
            self.connection.reply("IRC commands and bot tasks reloaded.")
