# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

import random

from earwigbot.commands import Command

class Access(Command):
    """Control and get info on who can access the bot."""
    name = "access"
    commands = ["access", "permission", "permissions", "perm", "perms"]

    def process(self, data):
        if not data.args:
            self.reply(data, "Subcommands are self, list, add, remove.")
            return
        db = self.config.irc["permissions"]
        if data.args[0] == "self":
            self.do_self(data)
        elif data.args[0] == "list":
            self.do_list(data)
        elif data.args[0] == "add":
            self.do_add(data)
        elif data.args[0] == "remove":
            self.do_remove(data)
        else:
            msg = "Unknown subcommand \x0303{0}\x0F.".format(data.args[0])
            self.reply(data, msg)

    def do_self(self, data):
        if db.is_owner(data):
            msg = "You are a bot owner (matching rule \x0302{0}\x0F)."
            self.reply(data, msg.format(db.is_owner(data)))
        elif db.is_admin(data):
            msg = "You are a bot admin (matching rule \x0302{0}\x0F)."
            self.reply(data, msg.format(db.is_admin(data)))
        else:
            self.reply(data, "You do not match any bot access rules.")

    def do_list(self, data):
        pass

    def do_add(self, data):
        pass

    def do_remove(self, data):
        pass
