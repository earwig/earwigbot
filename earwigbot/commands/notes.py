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

from os import path
import sqlite3 as sqlite
from threading import Lock

from earwigbot.commands import Command

class Notes(Command):
    """A mini IRC-based wiki for storing notes, tips, and reminders."""
    name = "notes"
    commands = ["notes", "note", "about"]
    version = 2

    def setup(self):
        self._dbfile = path.join(self.config.root_dir, "notes.db")
        self._db_access_lock = Lock()

    def process(self, data):
        commands = {
            "list": self.do_list,
            "read": self.do_read,
            "edit": self.do_edit,
            "info": self.do_info,
            "history": self.do_history,
            "rename": self.do_rename,
            "delete": self.do_delete,
        }

        if not data.args:
            msg = "\x0302The Earwig Mini-Wiki\x0F: running v{0}. Subcommands are: {1}. You can get help on any with '!{2} help subcommand'."
            cmnds = ", ".join((commands))
            self.reply(data, msg.format(self.version, cmnds, data.command))
            return
        command = data.args[0].lower()
        if command in commands:
            commands[command](data)
        else:
            self.reply("Unknown subcommand: \x0303{0}\x0F.".format(command))

    def create_db(self, conn):
        """Initialize the notes database with its necessary tables."""
        script = """
            CREATE TABLE entries (entry_id, entry_slug, entry_title, entry_revision);
            CREATE TABLE users (user_id, user_host);
            CREATE TABLE revisions (rev_id, rev_entry, rev_user, rev_timestamp, rev_content);
        """
        conn.executescript(script)

    def do_list(self, data):
        """Show a list of entries in the notes database."""
        query = "SELECT entry_title FROM entries"
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                entries = conn.execute(query).fetchall()
            except sqlite.OperationalError:
                entires = []

        if entries:
            self.reply(data, "Entries: {0}".format(", ".join(entries)))
        else:
            self.reply(data, "No entries in the database.")

    def do_read(self, data):
        """Read an entry from the notes database."""
        query = """SELECT entry_title, rev_content FROM entries
                   INNER JOIN revisions ON entry_revision = rev_id
                   WHERE entry_slug = ?"""
        try:
            slug = data.args[1].lower().replace("_", "").replace("-", "")
        except IndexError:
            self.reply(data, "Please name an entry to read from.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                title, content = conn.execute(query, (slug,)).fetchone()
            except sqlite.OperationalError:
                title, content = slug, None

        if content:
            self.reply(data, "\x0302{0}\x0F: {1}".format(title, content))
        else:
            self.reply(data, "Entry \x0302{0}\x0F not found.".format(title))

    def do_edit(self, data):
        """Edit an entry in the notes database."""
        pass

    def do_info(self, data):
        """Get info on an entry in the notes database."""
        pass

    def do_history(self, data):
        """Get the history of an entry in the notes database."""
        query = """SELECT entry_title, rev_timestamp, user_host FROM entries
                   INNER JOIN revisions ON entry_revision = rev_id
                   INNER JOIN users ON rev_user = user_id
                   WHERE entry_slug = ?"""
        try:
            slug = data.args[1].lower().replace("_", "").replace("-", "")
        except IndexError:
            self.reply(data, "Please name an entry to get the history of.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                data = conn.execute(query, (slug,)).fetchall()
            except sqlite.OperationalError:
                data = []

        if data:
            title = data[0][0]
            times = [datum[1] for datum in data]
            earliest = min(times).strftime("%b %d, %Y %H:%M:%S")
            msg = "\x0302{0}\x0F: {1} edits since {2}"
            msg = msg.format(title, len(data), earliest)
            if len(times) > 1:
                latest = max(times).strftime("%b %d, %Y %H:%M:%S")
                msg += "; last edit on {0}".format(lastest)
            names = [datum[2] for datum in data]
            msg += "; authors: {0}.".format(", ".join(list(set(names))))
            self.reply(data, msg)
        else:
            self.reply(data, "Entry \x0302{0}\x0F not found.".format(title))

    def do_rename(self, data):
        """Rename an entry in the notes database."""
        pass

    def do_delete(self, data):
        """Delete an entry from the notes database."""
        pass
