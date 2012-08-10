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

import re

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
            self.do_self(data, db)
        elif data.args[0] == "list":
            self.do_list(data, db)
        elif data.args[0] == "add":
            self.do_add(data, db)
        elif data.args[0] == "remove":
            self.do_remove(data, db)
        else:
            msg = "Unknown subcommand \x0303{0}\x0F.".format(data.args[0])
            self.reply(data, msg)

    def do_self(self, data, db):
        if db.is_owner(data):
            msg = "You are a bot owner (matching rule \x0302{0}\x0F)."
            self.reply(data, msg.format(db.is_owner(data)))
        elif db.is_admin(data):
            msg = "You are a bot admin (matching rule \x0302{0}\x0F)."
            self.reply(data, msg.format(db.is_admin(data)))
        else:
            self.reply(data, "You do not match any bot access rules.")

    def do_list(self, data, db):
        if len(data.args) > 1:
            if data.args[1] in ["owner", "owners"]:
                name, rules = "owners", db.data.get(db.OWNERS)
            elif data.args[1] in ["admin", "admins"]:
                name, rules = "admins", db.data.get(db.ADMINS)
            else:
                msg = "Unknown access level \x0302{0}\x0F."
                self.reply(data, msg.format(data.args[1]))
                return
            if rules:
                msg = "Bot {0}: {1}.".format(name, ", ".join(map(str, rules)))
            else:
                msg = "No bot {0}.".format(name)
            self.reply(data, msg)
        else:
            owners = len(db.data.get(db.OWNERS, []))
            admins = len(db.data.get(db.ADMINS, []))
            msg = "There are {0} bot owners and {1} bot admins. Use '!{2} list owners' or '!{2} list admins' for details."
            self.reply(data, msg.format(owners, admins, data.command))

    def do_add(self, data, db):
        user = self.get_user_from_args(data)
        if user:
            nick, ident, host = user
            if data.args[1] in ["owner", "owners"]:
                name, level, adder = "owner", db.OWNER, db.add_owner
            else:
                name, level, adder = "admin", db.ADMIN, db.add_admin
            if db.has_exact(nick, ident, host, level):
                rule = "{0}!{1}@{2}".format(nick, ident, host)
                msg = "\x0302{0}\x0F is already a bot {1}.".format(rule, name)
                self.reply(data, msg)
            else:
                rule = adder(nick, ident, host)
                msg = "Added bot {0} \x0302{1}\x0F.".format(name, rule)
                self.reply(data, msg)

    def do_remove(self, data, db):
        user = self.get_user_from_args(data)
        if user:
            nick, ident, host = user
            if data.args[1] in ["owner", "owners"]:
                name, level, rmver = "owner", db.OWNER, db.remove_owner
            else:
                name, level, rmver = "admin", db.ADMIN, db.remove_admin
            rule = rmver(nick, ident, host)
            if rule:
                msg = "Removed bot {0} \x0302{1}\x0F.".format(name, rule)
                self.reply(data, msg)
            else:
                rule = "{0}!{1}@{2}".format(nick, ident, host)
                msg = "No bot {0} matching \x0302{1}\x0F.".format(name, rule)
                self.reply(data, msg)

    def get_user_from_args(self, data):
        if not db.is_owner(data):
            msg = "You must be a bot owner to add users to the access list."
            self.reply(data, msg)
            return
        levels = ["owner", "owners", "admin", "admins"]
        if len(data.args) == 1 or data.args[1] not in levels:
            msg = "Please specify an access level ('owners' or 'admins')."
            self.reply(data, msg)
            return
        if len(data.args) == 2:
            self.no_arg_error(data)
            return
        if "nick" in data.kwargs or "ident" in kwargs or "host" in kwargs:
            nick = data.kwargs.get("nick", "*")
            ident = data.kwargs.get("ident", "*")
            host = data.kwargs.get("host", "*")
            return nick, ident, host
        user = re.match(r"(.*?)!(.*?)@(.*?)$", data.args[2])
        if not user:
            self.no_arg_error(data)
            return
        return user.group(1), user.group(2), user.group(3)

    def no_arg_error(self, data):
        msg = 'Please specify a user, either as "\x0302nick\x0F!\x0302ident\x0F@\x0302host\x0F"'
        msg += ' or "nick=\x0302nick\x0F, ident=\x0302ident\x0F, host=\x0302host\x0F".'
        self.reply(data, msg)
