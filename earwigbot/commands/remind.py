# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2016 Ben Kurtovic <ben.kurtovic@gmail.com>
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
from itertools import chain
import operator
import random
from threading import RLock, Thread
import time

from earwigbot.commands import Command
from earwigbot.irc import Data

DISPLAY = ["display", "show", "info", "details"]
CANCEL = ["cancel", "stop", "delete", "del", "stop", "unremind", "forget",
          "disregard"]
SNOOZE = ["snooze", "delay", "reset", "adjust", "modify", "change"]
SNOOZE_ONLY = ["snooze", "delay", "reset"]

def _format_time(epoch):
    """Format a UNIX timestamp nicely."""
    lctime = time.localtime(epoch)
    if lctime.tm_year == time.localtime().tm_year:
        return time.strftime("%b %d %H:%M:%S %Z", lctime)
    else:
        return time.strftime("%b %d, %Y %H:%M:%S %Z", lctime)


class Remind(Command):
    """Set a message to be repeated to you in a certain amount of time. See
    usage with !remind help."""
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
        if command in SNOOZE_ONLY:
            return "snooze"
        if command in SNOOZE:  # "adjust" == snoozing active reminders
            return "adjust"

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

        for unit, factor in time_units.iteritems():
            arg = arg.replace(unit, "*" + str(factor))

        try:
            parsed = int(_evaluate(ast.parse(arg, mode="eval").body))
        except (SyntaxError, KeyError):
            raise ValueError(arg)
        if parsed <= 0:
            raise ValueError(parsed)
        return parsed

    def _get_reminder_by_id(self, user, rid):
        """Return the _Reminder object that corresponds to a particular ID.

        Raises IndexError on failure.
        """
        rid = rid.upper()
        if user not in self.reminders:
            raise IndexError(rid)
        return [robj for robj in self.reminders[user] if robj.id == rid][0]

    def _get_new_id(self):
        """Get a free ID for a new reminder."""
        taken = set(robj.id for robj in chain(*self.reminders.values()))
        num = random.choice(list(set(range(4096)) - taken))
        return "R{0:03X}".format(num)

    def _start_reminder(self, reminder, user):
        """Start the given reminder object for the given user."""
        if user in self.reminders:
            self.reminders[user].append(reminder)
        else:
            self.reminders[user] = [reminder]
        self._thread.add(reminder)

    def _create_reminder(self, data):
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

        message = " ".join(data.args[1:])
        try:
            rid = self._get_new_id()
        except IndexError:
            msg = "Couldn't set a new reminder: no free IDs available."
            return self.reply(data, msg)

        reminder = _Reminder(rid, data.host, wait, message, data, self)
        self._start_reminder(reminder, data.host)
        msg = "Set reminder \x0303{0}\x0F ({1})."
        self.reply(data, msg.format(rid, reminder.end_time))

    def _display_reminder(self, data, reminder):
        """Display a particular reminder's information."""
        msg = 'Reminder \x0303{0}\x0F: {1} seconds ({2}): "{3}".'
        msg = msg.format(reminder.id, reminder.wait, reminder.end_time,
                         reminder.message)
        self.reply(data, msg)

    def _cancel_reminder(self, data, reminder):
        """Cancel a pending reminder."""
        self._thread.remove(reminder)
        self.unstore_reminder(reminder.id)
        self.reminders[data.host].remove(reminder)
        if not self.reminders[data.host]:
            del self.reminders[data.host]
        msg = "Reminder \x0303{0}\x0F canceled."
        self.reply(data, msg.format(reminder.id))

    def _snooze_reminder(self, data, reminder, arg=None):
        """Snooze a reminder to be re-triggered after a period of time."""
        verb = "snoozed" if reminder.expired else "adjusted"
        try:
            duration = self._parse_time(arg) if arg else None
        except ValueError:
            duration = None

        reminder.reset(duration)
        end = _format_time(reminder.end)
        msg = "Reminder \x0303{0}\x0F {1} until {2}."
        self.reply(data, msg.format(reminder.id, verb, end))

    def _load_reminders(self):
        """Load previously made reminders from the database."""
        permdb = self.config.irc["permissions"]
        try:
            database = permdb.get_attr("command:remind", "data")
        except KeyError:
            return
        permdb.set_attr("command:remind", "data", "[]")

        connect_wait = 30
        for item in ast.literal_eval(database):
            rid, user, wait, end, message, data = item
            if end < time.time() + connect_wait:
                # Make reminders that have expired while the bot was offline
                # trigger shortly after startup
                end = time.time() + connect_wait
            data = Data.unserialize(data)
            reminder = _Reminder(rid, user, wait, message, data, self, end)
            self._start_reminder(reminder, user)

    def _show_reminders(self, data):
        """Show all of a user's current reminders."""
        if data.host not in self.reminders:
            self.reply(data, "You have no reminders. Set one with "
                             "\x0306!remind [time] [message]\x0F. See also: "
                             "\x0306!remind help\x0F.")
            return

        shorten = lambda s: (s[:37] + "..." if len(s) > 40 else s)
        dest = lambda data: (
            "privately" if data.is_private else "in {0}".format(data.chan))
        fmt = lambda robj: '\x0303{0}\x0F ("{1}" {2}, {3})'.format(
            robj.id, shorten(robj.message), dest(robj.data), robj.end_time)

        rlist = ", ".join(fmt(robj) for robj in self.reminders[data.host])
        self.reply(data, "Your reminders: {0}.".format(rlist))

    def _show_all_reminders(self, data):
        """Show all reminders to bot admins."""
        if not self.config.irc["permissions"].is_admin(data):
            self.reply(data, "You must be a bot admin to view other users' "
                             "reminders. View your own with "
                             "\x0306!reminders\x0F.")
            return
        if not self.reminders:
            self.reply(data, "There are no active reminders.")
            return

        dest = lambda data: (
            "privately" if data.is_private else "in {0}".format(data.chan))
        fmt = lambda robj, user: '\x0303{0}\x0F (for {1} {2}, {3})'.format(
            robj.id, user, dest(robj.data), robj.end_time)

        rlist = (fmt(rem, user) for user, rems in self.reminders.iteritems()
                 for rem in rems)
        self.reply(data, "All reminders: {0}.".format(", ".join(rlist)))

    def _show_help(self, data):
        """Reply to the user with help for all major subcommands."""
        parts = [
            ("Add new", "!remind [time] [message]"),
            ("List all", "!reminders"),
            ("Get info", "!remind [id]"),
            ("Cancel", "!remind cancel [id]"),
            ("Adjust", "!remind adjust [id] [time]"),
            ("Restart", "!snooze [id] [time]"),
            ("Admin", "!remind all")
        ]
        extra = "The \x0306[id]\x0F can be omitted if you have only one reminder."
        joined = " ".join("{0}: \x0306{1}\x0F.".format(k, v) for k, v in parts)
        self.reply(data, joined + " " + extra)

    def _dispatch_command(self, data, command, args):
        """Handle a reminder-processing subcommand."""
        user = data.host
        reminder = None
        if args and args[0].upper().startswith("R"):
            try:
                reminder = self._get_reminder_by_id(user, args[0])
            except IndexError:
                msg = "Couldn't find a reminder for \x0302{0}\x0F with ID \x0303{1}\x0F."
                self.reply(data, msg.format(user, args[0]))
                return
            args.pop(0)
        elif user not in self.reminders:
            msg = "You have no reminders to {0}."
            self.reply(data, msg.format(self._normalize(command)))
            return
        elif len(self.reminders[user]) == 1:
            reminder = self.reminders[user][0]
        elif command in SNOOZE_ONLY:  # Select most recent expired reminder
            rmds = [rmd for rmd in self.reminders[user] if rmd.expired]
            rmds.sort(key=lambda rmd: rmd.end)
            if len(rmds) > 0:
                reminder = rmds[-1]
        elif command in SNOOZE or command in CANCEL:  # Select only active one
            rmds = [rmd for rmd in self.reminders[user] if not rmd.expired]
            if len(rmds) == 1:
                reminder = rmds[0]
        if not reminder:
            msg = "You have {0} reminders. {1} which one?"
            num = len(self.reminders[user])
            command = self._normalize(command).capitalize()
            self.reply(data, msg.format(num, command))
            return

        if command in DISPLAY:
            self._display_reminder(data, reminder)
        elif command in CANCEL:
            self._cancel_reminder(data, reminder)
        elif command in SNOOZE:
            self._snooze_reminder(data, reminder, args[0] if args else None)
        else:
            msg = "Unknown action \x02{0}\x0F for reminder \x0303{1}\x0F."
            self.reply(data, msg.format(command, reminder.id))

    def _process(self, data):
        """Main entry point."""
        if data.command in SNOOZE + CANCEL:
            return self._dispatch_command(data, data.command, data.args)
        if not data.args:
            return self._show_reminders(data)

        if data.args[0] == "help":
            return self._show_help(data)
        if data.args[0] == "list":
            return self._show_reminders(data)
        if data.args[0] == "all":
            return self._show_all_reminders(data)
        if data.args[0] in DISPLAY + CANCEL + SNOOZE:
            return self._dispatch_command(data, data.args[0], data.args[1:])

        try:
            self._get_reminder_by_id(data.host, data.args[0])
        except IndexError:
            return self._create_reminder(data)
        if len(data.args) == 1:
            return self._dispatch_command(data, "display", data.args)
        self._dispatch_command(
            data, data.args[1], [data.args[0]] + data.args[2:])

    @property
    def lock(self):
        """Return the reminder modification/access lock."""
        return self._lock

    def setup(self):
        self.reminders = {}
        self._lock = RLock()
        self._thread = _ReminderThread(self._lock)
        self._load_reminders()

    def process(self, data):
        with self.lock:
            self._process(data)

    def unload(self):
        self._thread.stop()

    def store_reminder(self, reminder):
        """Store a serialized reminder into the database."""
        permdb = self.config.irc["permissions"]
        try:
            dump = permdb.get_attr("command:remind", "data")
        except KeyError:
            dump = "[]"

        database = ast.literal_eval(dump)
        database.append(reminder)
        permdb.set_attr("command:remind", "data", str(database))

    def unstore_reminder(self, rid):
        """Remove a reminder from the database by ID."""
        permdb = self.config.irc["permissions"]
        try:
            dump = permdb.get_attr("command:remind", "data")
        except KeyError:
            dump = "[]"

        database = ast.literal_eval(dump)
        database = [item for item in database if item[0] != rid]
        permdb.set_attr("command:remind", "data", str(database))


class _ReminderThread(object):
    """A single thread that handles reminders."""

    def __init__(self, lock):
        self._thread = None
        self._abort = False
        self._active = {}
        self._lock = lock

    def _running(self):
        """Return if the thread should still be running."""
        return self._active and not self._abort

    def _get_soonest(self):
        """Get the soonest reminder to trigger."""
        return min(self._active.values(), key=lambda robj: robj.end)

    def _get_ready_reminder(self):
        """Block until a reminder is ready to be triggered."""
        while self._running():
            if self._get_soonest().end <= time.time():
                return self._get_soonest()
            self._lock.release()
            time.sleep(0.25)
            self._lock.acquire()

    def _callback(self):
        """Internal callback function to be executed by the reminder thread."""
        with self._lock:
            while True:
                reminder = self._get_ready_reminder()
                if not reminder:
                    break

                if reminder.trigger():
                    del self._active[reminder.id]
            self._thread = None

    def _start(self):
        """Start the thread."""
        self._thread = Thread(target=self._callback, name="reminder")
        self._thread.daemon = True
        self._thread.start()
        self._abort = False

    def add(self, reminder):
        """Add a reminder to the table of active reminders."""
        self._active[reminder.id] = reminder
        if not self._thread:
            self._start()

    def remove(self, reminder):
        """Remove a reminder from the table of active reminders."""
        if reminder.id in self._active:
            del self._active[reminder.id]
        if not self._active:
            self.stop()

    def stop(self):
        """Stop the thread."""
        if not self._thread:
            return
        self._abort = True
        self._thread = None


class _Reminder(object):
    """Represents a single reminder."""
    def __init__(self, rid, user, wait, message, data, cmdobj, end=None):
        self.id = rid
        self.wait = wait
        self.end = time.time() + wait if end is None else end
        self.message = message

        self._user = user
        self._data = data
        self._cmdobj = cmdobj
        self._expired = False

        self._save()

    def _save(self):
        """Save this reminder to the database."""
        data = self._data.serialize()
        item = (self.id, self._user, self.wait, self.end, self.message, data)
        self._cmdobj.store_reminder(item)

    def _fire(self):
        """Activate the reminder for the user."""
        self._cmdobj.reply(self._data, self.message)
        self._cmdobj.unstore_reminder(self.id)
        self.end = time.time() + (60 * 60 * 24)
        self._expired = True

    def _finalize(self):
        """Clean up after a reminder has been expired for too long."""
        try:
            self._cmdobj.reminders[self._user].remove(self)
            if not self._cmdobj.reminders[self._user]:
                del self._cmdobj.reminders[self._user]
        except (KeyError, ValueError):  # Already canceled by the user
            pass

    @property
    def data(self):
        """Return the IRC data object associated with this reminder."""
        return self._data

    @property
    def end_time(self):
        """Return a string representing the end time of a reminder."""
        if self._expired or self.end < time.time():
            return "expired"
        return "ends {0}".format(_format_time(self.end))

    @property
    def expired(self):
        """Return whether the reminder is expired."""
        return self._expired

    def reset(self, wait=None):
        """Reactivate a reminder."""
        if wait is not None:
            self.wait = wait
        self.end = self.wait + time.time()
        self._expired = False

        self._cmdobj.unstore_reminder(self.id)
        self._save()

    def trigger(self):
        """Hook run by the reminder thread."""
        if not self._expired:
            self._fire()
            return False
        else:
            self._finalize()
            return True
