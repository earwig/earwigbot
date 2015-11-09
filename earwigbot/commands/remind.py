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

import ast
from contextlib import contextmanager
from itertools import chain
import operator
import random
from threading import RLock, Thread
import time

from earwigbot.commands import Command
from earwigbot.irc import Data

DISPLAY = ["display", "show", "list", "info", "details"]
CANCEL = ["cancel", "stop", "delete", "del", "stop", "unremind", "forget",
          "disregard"]
SNOOZE = ["snooze", "delay", "reset", "adjust", "modify", "change"]

class Remind(Command):
    """Set a message to be repeated to you in a certain amount of time."""
    name = "remind"
    commands = ["remind", "reminder", "reminders", "snooze", "cancel",
                "unremind", "forget"]

    @staticmethod
    def _normalize(command):
        """Convert a command name into its canonical form."""
        if command in DISPLAY:
            return "display"
        if command in CANCEL:
            return "cancel"
        if command in SNOOZE:
            return "snooze"

    @staticmethod
    def _parse_time(arg):
        """Parse the wait time for a reminder."""
        ast_to_op = {
            ast.Add: operator.add, ast.Sub: operator.sub,
            ast.Mult: operator.mul, ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
            ast.Pow: operator.pow
        }
        time_units = {
            "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000
        }

        def _evaluate(node):
            """Convert an AST node into a real number or raise an exception."""
            if isinstance(node, ast.Num):
                if not isinstance(node.n, (int, long, float)):
                    raise ValueError(node.n)
                return node.n
            elif isinstance(node, ast.BinOp):
                left, right = _evaluate(node.left), _evaluate(node.right)
                return ast_to_op[type(node.op)](left, right)
            else:
                raise ValueError(node)

        if arg and arg[-1] in time_units:
            factor, arg = time_units[arg[-1]], arg[:-1]
        else:
            factor = 1

        try:
            parsed = int(_evaluate(ast.parse(arg, mode="eval").body) * factor)
        except (SyntaxError, KeyError):
            raise ValueError(arg)
        if parsed <= 0:
            raise ValueError(parsed)
        return parsed

    @contextmanager
    def _db(self):
        """Return a threadsafe context manager for the permissions database."""
        with self._db_lock:
            yield self.config.irc["permissions"]

    def _really_get_reminder_by_id(self, user, rid):
        """Return the _Reminder object that corresponds to a particular ID.

        Raises IndexError on failure.
        """
        rid = rid.upper()
        if user not in self.reminders:
            raise IndexError(rid)
        return [robj for robj in self.reminders[user] if robj.id == rid][0]

    def _get_reminder_by_id(self, user, rid, data):
        """Return the _Reminder object that corresponds to a particular ID.

        Sends an error message to the user on failure.
        """
        try:
            return self._really_get_reminder_by_id(user, rid)
        except IndexError:
            msg = "Couldn't find a reminder for \x0302{0}\x0F with ID \x0303{1}\x0F."
            self.reply(data, msg.format(user, rid))

    def _get_new_id(self):
        """Get a free ID for a new reminder."""
        taken = set(robj.id for robj in chain(*self.reminders.values()))
        num = random.choice(list(set(range(4096)) - taken))
        return "R{0:03X}".format(num)

    def _start_reminder(self, reminder, user):
        """Start the given reminder object for the given user."""
        reminder.start()
        if user in self.reminders:
            self.reminders[user].append(reminder)
        else:
            self.reminders[user] = [reminder]

    def _create_reminder(self, data, user):
        """Create a new reminder for the given user."""
        try:
            wait = self._parse_time(data.args[0])
        except ValueError:
            msg = "Invalid time \x02{0}\x0F. Time must be a positive integer, in seconds."
            return self.reply(data, msg.format(data.args[0]))

        if wait > 1000 * 365 * 24 * 60 * 60:
            # Hard to think of a good upper limit, but 1000 years works.
            msg = "Given time \x02{0}\x0F is too large. Keep it reasonable."
            return self.reply(data, msg.format(data.args[0]))

        end = time.time() + wait
        message = " ".join(data.args[1:])
        try:
            rid = self._get_new_id()
        except IndexError:
            msg = "Couldn't set a new reminder: no free IDs available."
            return self.reply(data, msg)

        reminder = _Reminder(rid, user, wait, end, message, data, self)
        self._start_reminder(reminder, user)
        msg = "Set reminder \x0303{0}\x0F ({1})."
        self.reply(data, msg.format(rid, reminder.end_time))

    def _display_reminder(self, data, reminder):
        """Display a particular reminder's information."""
        msg = 'Reminder \x0303{0}\x0F: {1} seconds ({2}): "{3}".'
        msg = msg.format(reminder.id, reminder.wait, reminder.end_time,
                         reminder.message)
        self.reply(data, msg)

    def _cancel_reminder(self, data, user, reminder):
        """Cancel a pending reminder."""
        reminder.stop()
        self.reminders[user].remove(reminder)
        if not self.reminders[user]:
            del self.reminders[user]
        msg = "Reminder \x0303{0}\x0F canceled."
        self.reply(data, msg.format(reminder.id))

    def _snooze_reminder(self, data, reminder, arg=None):
        """Snooze a reminder to be re-triggered after a period of time."""
        verb = "snoozed" if reminder.end < time.time() else "adjusted"
        if arg:
            try:
                duration = self._parse_time(data.args[arg])
                reminder.wait = duration
            except (IndexError, ValueError):
                pass

        reminder.end = time.time() + reminder.wait
        reminder.start()
        end = time.strftime("%b %d %H:%M:%S %Z", time.localtime(reminder.end))
        msg = "Reminder \x0303{0}\x0F {1} until {2}."
        self.reply(data, msg.format(reminder.id, verb, end))

    def _load_reminders(self):
        """Load previously made reminders from the database."""
        with self._db() as permdb:
            try:
                database = permdb.get_attr("command:remind", "data")
            except KeyError:
                return
            permdb.set_attr("command:remind", "data", "[]")

        for item in ast.literal_eval(database):
            rid, user, wait, end, message, data = item
            if end < time.time():
                continue
            data = Data.unserialize(data)
            reminder = _Reminder(rid, user, wait, end, message, data, self)
            self._start_reminder(reminder, user)

    def _handle_command(self, command, data, user, reminder, arg=None):
        """Handle a reminder-processing subcommand."""
        if command in DISPLAY:
            self._display_reminder(data, reminder)
        elif command in CANCEL:
            self._cancel_reminder(data, user, reminder)
        elif command in SNOOZE:
            self._snooze_reminder(data, reminder, arg)
        else:
            msg = "Unknown action \x02{0}\x0F for reminder \x0303{1}\x0F."
            self.reply(data, msg.format(command, reminder.id))

    def _show_reminders(self, data, user):
        """Show all of a user's current reminders."""
        shorten = lambda s: (s[:37] + "..." if len(s) > 40 else s)
        tmpl = '\x0303{0}\x0F ("{1}", {2})'
        fmt = lambda robj: tmpl.format(robj.id, shorten(robj.message),
                                       robj.end_time)

        if user in self.reminders:
            rlist = ", ".join(fmt(robj) for robj in self.reminders[user])
            msg = "Your reminders: {0}.".format(rlist)
        else:
            msg = ("You have no reminders. Set one with \x0306!remind [time] "
                   "[message]\x0F. See also: \x0306!remind help\x0F.")
        self.reply(data, msg)

    def _process_snooze_command(self, data, user):
        """Process the !snooze command."""
        if not data.args:
            if user not in self.reminders:
                self.reply(data, "You have no reminders to snooze.")
            elif len(self.reminders[user]) == 1:
                self._snooze_reminder(data, self.reminders[user][0])
            else:
                msg = "You have {0} reminders. Snooze which one?"
                self.reply(data, msg.format(len(self.reminders[user])))
            return
        reminder = self._get_reminder_by_id(user, data.args[0], data)
        if reminder:
            self._snooze_reminder(data, reminder, 1)

    def _process_cancel_command(self, data, user):
        """Process the !cancel, !unremind, and !forget commands."""
        if not data.args:
            if user not in self.reminders:
                self.reply(data, "You have no reminders to cancel.")
            elif len(self.reminders[user]) == 1:
                self._cancel_reminder(data, user, self.reminders[user][0])
            else:
                msg = "You have {0} reminders. Cancel which one?"
                self.reply(data, msg.format(len(self.reminders[user])))
            return
        reminder = self._get_reminder_by_id(user, data.args[0], data)
        if reminder:
            self._cancel_reminder(data, user, reminder)

    def _show_help(self, data):
        """Reply to the user with help for all major subcommands."""
        parts = [
            ("Add new", "!remind [time] [message]"),
            ("List all", "!reminders"),
            ("Get info", "!remind [id]"),
            ("Cancel", "!remind cancel [id]"),
            ("Adjust", "!remind adjust [id] [time]"),
            ("Restart", "!snooze [id]")
        ]
        extra = "In most cases, \x0306[id]\x0F can be omitted if you have only one reminder."
        joined = " ".join("{0}: \x0306{1}\x0F.".format(k, v) for k, v in parts)
        self.reply(data, joined + " " + extra)

    def setup(self):
        self.reminders = {}
        self._db_lock = RLock()
        self._load_reminders()

    def process(self, data):
        if data.command == "snooze":
            return self._process_snooze_command(data, data.host)
        if data.command in ["cancel", "unremind", "forget"]:
            return self._process_cancel_command(data, data.host)
        if not data.args:
            return self._show_reminders(data, data.host)

        user = data.host
        if len(data.args) == 1:
            command = data.args[0]
            if command == "help":
                return self._show_help(data)
            if command in DISPLAY + CANCEL + SNOOZE:
                if user not in self.reminders:
                    msg = "You have no reminders to {0}."
                    self.reply(data, msg.format(self._normalize(command)))
                elif len(self.reminders[user]) == 1:
                    reminder = self.reminders[user][0]
                    self._handle_command(command, data, user, reminder)
                else:
                    msg = "You have {0} reminders. {1} which one?"
                    num = len(self.reminders[user])
                    command = self._normalize(command).capitalize()
                    self.reply(data, msg.format(num, command))
                return
            reminder = self._get_reminder_by_id(user, data.args[0], data)
            if reminder:
                self._display_reminder(data, reminder)
            return

        if data.args[0] in DISPLAY + CANCEL + SNOOZE:
            reminder = self._get_reminder_by_id(user, data.args[1], data)
            if reminder:
                self._handle_command(data.args[0], data, user, reminder, 2)
            return

        try:
            reminder = self._really_get_reminder_by_id(user, data.args[0])
        except IndexError:
            return self._create_reminder(data, user)

        self._handle_command(data.args[1], data, user, reminder, 2)

    def unload(self):
        for reminder in chain(*self.reminders.values()):
            reminder.stop(delete=False)

    def store_reminder(self, reminder):
        """Store a serialized reminder into the database."""
        with self._db() as permdb:
            try:
                dump = permdb.get_attr("command:remind", "data")
            except KeyError:
                dump = "[]"

            database = ast.literal_eval(dump)
            database.append(reminder)
            permdb.set_attr("command:remind", "data", str(database))

    def unstore_reminder(self, rid):
        """Remove a reminder from the database by ID."""
        with self._db() as permdb:
            try:
                dump = permdb.get_attr("command:remind", "data")
            except KeyError:
                dump = "[]"

            database = ast.literal_eval(dump)
            database = [item for item in database if item[0] != rid]
            permdb.set_attr("command:remind", "data", str(database))

class _Reminder(object):
    """Represents a single reminder."""

    def __init__(self, rid, user, wait, end, message, data, cmdobj):
        self.id = rid
        self.wait = wait
        self.end = end
        self.message = message

        self._user = user
        self._data = data
        self._cmdobj = cmdobj
        self._thread = None

    def _callback(self):
        """Internal callback function to be executed by the reminder thread."""
        thread = self._thread
        while time.time() < thread.end:
            time.sleep(1)
            if thread.abort:
                return
        self._cmdobj.reply(self._data, self.message)
        self._delete()
        for i in xrange(60):
            time.sleep(1)
            if thread.abort:
                return
        try:
            self._cmdobj.reminders[self._user].remove(self)
            if not self._cmdobj.reminders[self._user]:
                del self._cmdobj.reminders[self._user]
        except (KeyError, ValueError):  # Already canceled by the user
            pass

    def _save(self):
        """Save this reminder to the database."""
        data = self._data.serialize()
        item = (self.id, self._user, self.wait, self.end, self.message, data)
        self._cmdobj.store_reminder(item)

    def _delete(self):
        """Remove this reminder from the database."""
        self._cmdobj.unstore_reminder(self.id)

    @property
    def end_time(self):
        """Return a string representing the end time of a reminder."""
        if self.end >= time.time():
            lctime = time.localtime(self.end)
            if lctime.tm_year == time.localtime().tm_year:
                ends = time.strftime("%b %d %H:%M:%S %Z", lctime)
            else:
                ends = time.strftime("%b %d, %Y %H:%M:%S %Z", lctime)
            return "ends {0}".format(ends)
        return "expired"

    def start(self):
        """Start the reminder timer thread. Stops it if already running."""
        self.stop()
        self._thread = Thread(target=self._callback, name="remind-" + self.id)
        self._thread.end = self.end
        self._thread.daemon = True
        self._thread.abort = False
        self._thread.start()
        self._save()

    def stop(self, delete=True):
        """Stop a currently running reminder."""
        if not self._thread:
            return
        if delete:
            self._delete()
        self._thread.abort = True
        self._thread = None
