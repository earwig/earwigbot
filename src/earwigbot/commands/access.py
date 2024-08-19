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

import re

from earwigbot.commands import Command


class Access(Command):
    """Control and get info on who can access the bot."""

    name = "access"
    commands = ["access", "permission", "permissions", "perm", "perms"]

    def process(self, data):
        permdb = self.config.irc["permissions"]
        if not data.args or data.args[0] == "self":
            self.do_self(data, permdb)
        elif data.args[0] == "list":
            self.do_list(data, permdb)
        elif data.args[0] == "add":
            self.do_add(data, permdb)
        elif data.args[0] == "remove":
            self.do_remove(data, permdb)
        elif data.args[0] == "help":
            self.reply(data, "Subcommands are self, list, add, and remove.")
        else:
            msg = "Unknown subcommand \x0303{0}\x0f. Subcommands are self, list, add, remove."
            self.reply(data, msg.format(data.args[0]))

    def do_self(self, data, permdb):
        if permdb.is_owner(data):
            msg = "You are a bot owner (matching rule \x0302{0}\x0f)."
            self.reply(data, msg.format(permdb.is_owner(data)))
        elif permdb.is_admin(data):
            msg = "You are a bot admin (matching rule \x0302{0}\x0f)."
            self.reply(data, msg.format(permdb.is_admin(data)))
        else:
            self.reply(data, "You do not match any bot access rules.")

    def do_list(self, data, permdb):
        if len(data.args) > 1:
            if data.args[1] in ["owner", "owners"]:
                name, rules = "owners", permdb.users.get(permdb.OWNER)
            elif data.args[1] in ["admin", "admins"]:
                name, rules = "admins", permdb.users.get(permdb.ADMIN)
            else:
                msg = "Unknown access level \x0302{0}\x0f."
                self.reply(data, msg.format(data.args[1]))
                return
            if rules:
                msg = "Bot {}: {}.".format(name, ", ".join(map(str, rules)))
            else:
                msg = f"No bot {name}."
            self.reply(data, msg)
        else:
            owners = len(permdb.users.get(permdb.OWNER, []))
            admins = len(permdb.users.get(permdb.ADMIN, []))
            msg = "There are \x02{0}\x0f bot owners and \x02{1}\x0f bot admins. Use '!{2} list owners' or '!{2} list admins' for details."
            self.reply(data, msg.format(owners, admins, data.command))

    def do_add(self, data, permdb):
        user = self.get_user_from_args(data, permdb)
        if user:
            nick, ident, host = user
            if data.args[1] in ["owner", "owners"]:
                name, level, adder = "owner", permdb.OWNER, permdb.add_owner
            else:
                name, level, adder = "admin", permdb.ADMIN, permdb.add_admin
            if permdb.has_exact(level, nick, ident, host):
                rule = f"{nick}!{ident}@{host}"
                msg = f"\x0302{rule}\x0f is already a bot {name}."
                self.reply(data, msg)
            else:
                rule = adder(nick, ident, host)
                msg = f"Added bot {name} \x0302{rule}\x0f."
                self.reply(data, msg)

    def do_remove(self, data, permdb):
        user = self.get_user_from_args(data, permdb)
        if user:
            nick, ident, host = user
            if data.args[1] in ["owner", "owners"]:
                name, rmver = "owner", permdb.remove_owner
            else:
                name, rmver = "admin", permdb.remove_admin
            rule = rmver(nick, ident, host)
            if rule:
                msg = f"Removed bot {name} \x0302{rule}\x0f."
                self.reply(data, msg)
            else:
                rule = f"{nick}!{ident}@{host}"
                msg = f"No bot {name} matching \x0302{rule}\x0f."
                self.reply(data, msg)

    def get_user_from_args(self, data, permdb):
        if not permdb.is_owner(data):
            msg = "You must be a bot owner to add or remove users to the access list."
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
        kwargs = data.kwargs
        if "nick" in kwargs or "ident" in kwargs or "host" in kwargs:
            nick = kwargs.get("nick", "*")
            ident = kwargs.get("ident", "*")
            host = kwargs.get("host", "*")
            return nick, ident, host
        user = re.match(r"(.*?)!(.*?)@(.*?)$", data.args[2])
        if not user:
            self.no_arg_error(data)
            return
        return user.group(1), user.group(2), user.group(3)

    def no_arg_error(self, data):
        msg = 'Please specify a user, either as "\x0302nick\x0f!\x0302ident\x0f@\x0302host\x0f"'
        msg += ' or "nick=\x0302nick\x0f, ident=\x0302ident\x0f, host=\x0302host\x0f".'
        self.reply(data, msg)
