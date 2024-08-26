# Copyright (C) 2009-2021 Ben Kurtovic <ben.kurtovic@gmail.com>
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
from ast import literal_eval

from earwigbot.commands import Command
from earwigbot.irc import RC


class Stalk(Command):
    """Stalk a particular user (!stalk/!unstalk) or page (!watch/!unwatch) for
    edits. Prefix regular expressions with "re:" (uses re.match)."""

    name = "stalk"
    commands = [
        "stalk",
        "watch",
        "unstalk",
        "unwatch",
        "stalks",
        "watches",
        "allstalks",
        "allwatches",
        "unstalkall",
        "unwatchall",
    ]
    hooks = ["msg", "rc"]
    MAX_STALKS_PER_USER = 5

    def setup(self):
        self._users = {}
        self._pages = {}
        self._load_stalks()

    def check(self, data):
        if isinstance(data, RC):
            return True
        if data.is_command and data.command in self.commands:
            return True
        return False

    def process(self, data):
        if isinstance(data, RC):
            self._process_rc(data)
            return

        data.is_admin = self.config.irc["permissions"].is_admin(data)

        if data.command.startswith("all"):
            if data.is_admin:
                self.reply(data, self._all_stalks())
            else:
                self.reply(
                    data,
                    "You must be a bot admin to view all stalked "
                    "users or watched pages. View your own with "
                    "\x0306!stalks\x0f.",
                )
            return

        if data.command.endswith("all"):
            if not data.is_admin:
                self.reply(
                    data,
                    "You must be a bot admin to unstalk a user "
                    "or unwatch a page for all users.",
                )
                return
            if not data.args:
                self.reply(
                    data,
                    "You must give a user to unstalk or a page "
                    "to unwatch. View all active with "
                    "\x0306!allstalks\x0f.",
                )
                return

        if not data.args or data.command in ["stalks", "watches"]:
            self.reply(data, self._current_stalks(data.nick))
            return

        modifiers = {}
        for modifier in ["noping", "nobots", "nominor", "nocolor"]:
            if "!" + modifier in data.args:
                modifiers[modifier] = True
                data.args.remove("!" + modifier)

        target = " ".join(data.args).replace("_", " ")
        if target.startswith("[[") and target.endswith("]]"):
            target = target[2:-2]
        if target.startswith("re:"):
            target = "re:" + target[3:].lstrip()
        else:
            if target.startswith("User:") and "stalk" in data.command:
                target = target[5:]
            target = target[0].upper() + target[1:]

        if data.command in ["stalk", "watch"]:
            if data.is_private:
                stalkinfo = (data.nick, None, modifiers)
            elif not data.is_admin:
                self.reply(
                    data,
                    "You must be a bot admin to stalk users or "
                    "watch pages publicly. Retry this command in "
                    "a private message.",
                )
                return
            else:
                stalkinfo = (data.nick, data.chan, modifiers)
        else:
            stalkinfo = None

        if data.command == "stalk":
            self._add_stalk("user", data, target, stalkinfo)
        elif data.command == "watch":
            self._add_stalk("page", data, target, stalkinfo)
        elif data.command == "unstalk":
            self._remove_stalk("user", data, target)
        elif data.command == "unwatch":
            self._remove_stalk("page", data, target)
        elif data.command == "unstalkall":
            self._remove_all_stalks("user", data, target)
        elif data.command == "unwatchall":
            self._remove_all_stalks("page", data, target)

    def _process_rc(self, rc):
        """Process a watcher event."""

        def _update_chans(items, flags):
            for item in items:
                modifiers = item[2] if len(item) > 2 else {}
                if modifiers.get("nobots") and "B" in flags:
                    continue
                if modifiers.get("nominor") and "M" in flags:
                    continue
                if item[1]:
                    if modifiers.get("noping"):
                        if item[1] not in chans:
                            chans[item[1]] = set()
                    elif item[1] in chans:
                        chans[item[1]].add(item[0])
                    else:
                        chans[item[1]] = {item[0]}
                    if modifiers.get("nocolor"):
                        nocolor.add(item[1])
                else:
                    chans[item[0]] = None
                    if modifiers.get("nocolor"):
                        nocolor.add(item[0])

        def _regex_match(target, tag):
            return target.startswith("re:") and re.match(target[3:], tag)

        def _process(table, tag, flags):
            for target, stalks in table.items():
                if target == tag or _regex_match(target, tag):
                    _update_chans(stalks, flags)

        chans = {}
        nocolor = set()
        _process(self._users, rc.user, rc.flags)
        if rc.is_edit:
            _process(self._pages, rc.page, rc.flags)
        if not chans:
            return

        with self.bot.component_lock:
            frontend = self.bot.frontend
            if frontend and not frontend.is_stopped():
                for chan, users in chans.items():
                    if chan.startswith("#") and chan not in frontend.channels:
                        continue
                    pretty = rc.prettify(color=chan not in nocolor)
                    if users:
                        nicks = ", ".join(sorted(users))
                        msg = f"\x02{nicks}\x0f: {pretty}"
                    else:
                        msg = pretty
                    if len(msg) > 400:
                        msg = msg[:397] + "..."
                    frontend.say(chan, msg)

    @staticmethod
    def _get_stalks_by_nick(nick, table):
        """Return a dictionary of stalklist entries by the given nick."""
        entries = {}
        for target, stalks in table.items():
            for info in stalks:
                if info[0] == nick:
                    if target in entries:
                        entries[target].append(info[1])
                    else:
                        entries[target] = [info[1]]
        return entries

    def _add_stalk(self, stalktype, data, target, stalkinfo):
        """Add a stalk entry to the given table."""
        if stalktype == "user":
            table = self._users
            verb = "stalk"
        else:
            table = self._pages
            verb = "watch"

        if not data.is_admin:
            nstalks = len(self._get_stalks_by_nick(data.nick, table))
            if nstalks >= self.MAX_STALKS_PER_USER:
                msg = (
                    "Already {0}ing {1} {2}s for you, which is the limit "
                    "for non-bot admins."
                )
                self.reply(data, msg.format(verb, nstalks, stalktype))
                return
            if stalkinfo[1] and not stalkinfo[1].startswith("##"):
                msg = "You must be a bot admin to {0} {1}s in public channels."
                self.reply(data, msg.format(verb, stalktype))
                return

        if target in table:
            if stalkinfo in table[target]:
                msg = "Already {0}ing that {1} in here for you."
                self.reply(data, msg.format(verb, stalktype))
                return
            else:
                table[target].append(stalkinfo)
        else:
            table[target] = [stalkinfo]

        msg = "Now {0}ing {1} \x0302{2}\x0f. Remove with \x0306!un{0} {2}\x0f."
        self.reply(data, msg.format(verb, stalktype, target))
        self._save_stalks()

    def _remove_stalk(self, stalktype, data, target):
        """Remove a stalk entry from the given table."""
        if stalktype == "user":
            table = self._users
            verb = "stalk"
            plural = "stalks"
        else:
            table = self._pages
            verb = "watch"
            plural = "watches"

        to_remove = []
        if target in table:
            for info in table[target]:
                if info[0] == data.nick:
                    to_remove.append(info)

        if not to_remove:
            msg = (
                "I haven't been {0}ing that {1} for you in the first "
                "place. View your active {2} with \x0306!{2}\x0f."
            )
            if data.is_admin:
                msg += (
                    " As a bot admin, you can clear all active {2} on "
                    "that {1} with \x0306!un{0}all {3}\x0f."
                )
            self.reply(data, msg.format(verb, stalktype, plural, target))
            return

        for info in to_remove:
            table[target].remove(info)
        if not table[target]:
            del table[target]
        msg = "No longer {0}ing {1} \x0302{2}\x0f for you."
        self.reply(data, msg.format(verb, stalktype, target))
        self._save_stalks()

    def _remove_all_stalks(self, stalktype, data, target):
        """Remove all entries for a particular target from the given table."""
        if stalktype == "user":
            table = self._users
            verb = "stalk"
            plural = "stalks"
        else:
            table = self._pages
            verb = "watch"
            plural = "watches"

        try:
            del table[target]
        except KeyError:
            msg = (
                "I haven't been {0}ing that {1} for anyone in the first "
                "place. View all active {2} with \x0306!all{2}\x0f."
            )
            self.reply(data, msg.format(verb, stalktype, plural))
        else:
            msg = "No longer {0}ing {1} \x0302{2}\x0f for anyone."
            self.reply(data, msg.format(verb, stalktype, target))
            self._save_stalks()

    def _current_stalks(self, nick):
        """Return the given user's current stalks."""

        def _format_chans(chans):
            if None in chans:
                chans.remove(None)
                if not chans:
                    return "privately"
                if len(chans) == 1:
                    return f"in {chans[0]} and privately"
                return "in " + ", ".join(chans) + ", and privately"
            return "in " + ", ".join(chans)

        def _format_stalks(stalks):
            return ", ".join(
                f"\x0302{target}\x0f ({_format_chans(chans)})"
                for target, chans in stalks.items()
            )

        users = self._get_stalks_by_nick(nick, self._users)
        pages = self._get_stalks_by_nick(nick, self._pages)
        uinfo = f" Users: {_format_stalks(users)}." if users else None
        pinfo = f" Pages: {_format_stalks(pages)}." if pages else None

        msg = "Currently stalking {0} user{1} and watching {2} page{3} for you.{4}{5}"
        return msg.format(
            len(users),
            "s" if len(users) != 1 else "",
            len(pages),
            "s" if len(pages) != 1 else "",
            uinfo if users else "",
            pinfo if pages else "",
        )

    def _all_stalks(self):
        """Return all existing stalks, for bot admins."""

        def _format_info(info):
            if info[1]:
                result = f"for {info[0]} in {info[1]}"
            else:
                result = f"for {info[0]} privately"
            modifiers = ", ".join(info[2]) if len(info) > 2 else ""
            if modifiers:
                result += f" ({modifiers})"
            return result

        def _format_data(data):
            return ", ".join(_format_info(info) for info in data)

        def _format_stalks(stalks):
            return ", ".join(
                f"\x0302{target}\x0f ({_format_data(data)})"
                for target, data in stalks.items()
            )

        users, pages = self._users, self._pages
        uinfo = f" Users: {_format_stalks(users)}." if users else None
        pinfo = f" Pages: {_format_stalks(pages)}." if pages else None

        msg = "Currently stalking {0} user{1} and watching {2} page{3}.{4}{5}"
        return msg.format(
            len(users),
            "s" if len(users) != 1 else "",
            len(pages),
            "s" if len(pages) != 1 else "",
            uinfo if users else "",
            pinfo if pages else "",
        )

    def _load_stalks(self):
        """Load saved stalks from the database."""
        permdb = self.config.irc["permissions"]
        try:
            data = permdb.get_attr("command:stalk", "data")
        except KeyError:
            return
        self._users, self._pages = literal_eval(data)

    def _save_stalks(self):
        """Save stalks to the database."""
        permdb = self.config.irc["permissions"]
        data = str((self._users, self._pages))
        permdb.set_attr("command:stalk", "data", data)
