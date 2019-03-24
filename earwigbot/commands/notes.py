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

from datetime import datetime
from os import path
import re
import sqlite3 as sqlite
from threading import Lock

from earwigbot.commands import Command

class Notes(Command):
    """A mini IRC-based wiki for storing notes, tips, and reminders."""
    name = "notes"
    commands = ["notes", "note", "about"]
    version = "2.1"

    aliases = {
        "all": "list",
        "show": "read",
        "get": "read",
        "add": "edit",
        "write": "edit",
        "change": "edit",
        "modify": "edit",
        "move": "rename",
        "remove": "delete"
    }

    def setup(self):
        self._dbfile = path.join(self.config.root_dir, "notes.db")
        self._db_access_lock = Lock()

    def process(self, data):
        commands = {
            "help": self.do_help,
            "list": self.do_list,
            "read": self.do_read,
            "edit": self.do_edit,
            "info": self.do_info,
            "rename": self.do_rename,
            "delete": self.do_delete,
        }

        if not data.args:
            self.do_help(data)
            return
        command = data.args[0].lower()
        if command in commands:
            commands[command](data)
        elif command in self.aliases:
            commands[self.aliases[command]](data)
        else:
            msg = "Unknown subcommand: \x0303{0}\x0F.".format(command)
            self.reply(data, msg)

    def do_help(self, data):
        """Get help on a subcommand."""
        info = {
            "help": "Get help on other subcommands.",
            "list": "List existing entries.",
            "read": "Read an existing entry ('!notes read [name]').",
            "edit": """Modify or create a new entry ('!notes edit name
                       [entry content]...'). If modifying, you must be the
                       entry author or a bot admin.""",
            "info": """Get information on an existing entry ('!notes info
                       [name]').""",
            "rename": """Rename an existing entry ('!notes rename [old_name]
                         [new_name]'). You must be the entry author or a bot
                         admin.""",
            "delete": """Delete an existing entry ('!notes delete [name]'). You
                         must be the entry author or a bot admin.""",
        }

        try:
            command = data.args[1]
        except IndexError:
            msg = ("\x0302The Earwig Mini-Wiki\x0F: running v{0}. Subcommands "
                   "are: {1}. You can get help on any with '!{2} help subcommand'.")
            cmnds = ", ".join((info.keys()))
            self.reply(data, msg.format(self.version, cmnds, data.command))
            return
        if command in self.aliases:
            command = self.aliases[command]
        try:
            help_ = re.sub(r"\s\s+", " ", info[command].replace("\n", ""))
            self.reply(data, "\x0303{0}\x0F: ".format(command) + help_)
        except KeyError:
            msg = "Unknown subcommand: \x0303{0}\x0F.".format(command)
            self.reply(data, msg)

    def do_list(self, data):
        """Show a list of entries in the notes database."""
        query = "SELECT entry_title FROM entries"
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                entries = conn.execute(query).fetchall()
            except sqlite.OperationalError:
                entries = []

        if entries:
            entries = [entry[0].encode("utf8") for entry in entries]
            self.reply(data, "Entries: {0}".format(", ".join(entries)))
        else:
            self.reply(data, "No entries in the database.")

    def do_read(self, data):
        """Read an entry from the notes database."""
        query = """SELECT entry_title, rev_content FROM entries
                   INNER JOIN revisions ON entry_revision = rev_id
                   WHERE entry_slug = ?"""
        try:
            slug = self._slugify(data.args[1])
        except IndexError:
            self.reply(data, "Please specify an entry to read from.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                title, content = conn.execute(query, (slug,)).fetchone()
            except (sqlite.OperationalError, TypeError):
                title, content = slug, None

        title = title.encode("utf8")
        if content:
            msg = "\x0302{0}\x0F: {1}"
            self.reply(data, msg.format(title, content.encode("utf8")))
        else:
            self.reply(data, "Entry \x0302{0}\x0F not found.".format(title))

    def do_edit(self, data):
        """Edit an entry in the notes database."""
        query1 = """SELECT entry_id, entry_title, user_host FROM entries
                    INNER JOIN revisions ON entry_revision = rev_id
                    INNER JOIN users ON rev_user = user_id
                    WHERE entry_slug = ?"""
        query2 = "INSERT INTO revisions VALUES (?, ?, ?, ?, ?)"
        query3 = "INSERT INTO entries VALUES (?, ?, ?, ?)"
        query4 = "UPDATE entries SET entry_revision = ? WHERE entry_id = ?"
        try:
            slug = self._slugify(data.args[1])
        except IndexError:
            self.reply(data, "Please specify an entry to edit.")
            return
        content = " ".join(data.args[2:]).strip().decode("utf8")
        if not content:
            self.reply(data, "Please give some content to put in the entry.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            create = True
            try:
                id_, title, author = conn.execute(query1, (slug,)).fetchone()
                create = False
            except sqlite.OperationalError:
                id_, title, author = 1, data.args[1].decode("utf8"), data.host
                self._create_db(conn)
            except TypeError:
                id_ = self._get_next_entry(conn)
                title, author = data.args[1].decode("utf8"), data.host
            permdb = self.config.irc["permissions"]
            if author != data.host and not permdb.is_admin(data):
                msg = "You must be an author or a bot admin to edit this entry."
                self.reply(data, msg)
                return
            revid = self._get_next_revision(conn)
            userid = self._get_user(conn, data.host)
            now = datetime.utcnow().strftime("%b %d, %Y %H:%M:%S")
            conn.execute(query2, (revid, id_, userid, now, content))
            if create:
                conn.execute(query3, (id_, slug, title, revid))
            else:
                conn.execute(query4, (revid, id_))

        msg = "Entry \x0302{0}\x0F updated."
        self.reply(data, msg.format(title.encode("utf8")))

    def do_info(self, data):
        """Get info on an entry in the notes database."""
        query = """SELECT entry_title, rev_timestamp, user_host FROM entries
                   INNER JOIN revisions ON entry_id = rev_entry
                   INNER JOIN users ON rev_user = user_id
                   WHERE entry_slug = ?"""
        try:
            slug = self._slugify(data.args[1])
        except IndexError:
            self.reply(data, "Please specify an entry to get info on.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                info = conn.execute(query, (slug,)).fetchall()
            except sqlite.OperationalError:
                info = []

        if info:
            title = info[0][0]
            times = [datum[1] for datum in info]
            earliest = min(times)
            msg = "\x0302{0}\x0F: {1} edits since {2}"
            msg = msg.format(title.encode("utf8"), len(info), earliest)
            if len(times) > 1:
                latest = max(times)
                msg += "; last edit on {0}".format(latest)
            names = [datum[2] for datum in info]
            msg += "; authors: {0}.".format(", ".join(list(set(names))))
            self.reply(data, msg)
        else:
            title = data.args[1]
            self.reply(data, "Entry \x0302{0}\x0F not found.".format(title))

    def do_rename(self, data):
        """Rename an entry in the notes database."""
        query1 = """SELECT entry_id, user_host FROM entries
                    INNER JOIN revisions ON entry_revision = rev_id
                    INNER JOIN users ON rev_user = user_id
                    WHERE entry_slug = ?"""
        query2 = """UPDATE entries SET entry_slug = ?, entry_title = ?
                    WHERE entry_id = ?"""
        try:
            slug = self._slugify(data.args[1])
        except IndexError:
            self.reply(data, "Please specify an entry to rename.")
            return
        try:
            newtitle = data.args[2]
        except IndexError:
            self.reply(data, "Please specify a new name for the entry.")
            return
        if newtitle == data.args[1]:
            self.reply(data, "The old and new names are identical.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                id_, author = conn.execute(query1, (slug,)).fetchone()
            except (sqlite.OperationalError, TypeError):
                msg = "Entry \x0302{0}\x0F not found.".format(data.args[1])
                self.reply(data, msg)
                return
            permdb = self.config.irc["permissions"]
            if author != data.host and not permdb.is_admin(data):
                msg = "You must be an author or a bot admin to rename this entry."
                self.reply(data, msg)
                return
            args = (self._slugify(newtitle), newtitle.decode("utf8"), id_)
            conn.execute(query2, args)

        msg = "Entry \x0302{0}\x0F renamed to \x0302{1}\x0F."
        self.reply(data, msg.format(data.args[1], newtitle))

    def do_delete(self, data):
        """Delete an entry from the notes database."""
        query1 = """SELECT entry_id, user_host FROM entries
                    INNER JOIN revisions ON entry_revision = rev_id
                    INNER JOIN users ON rev_user = user_id
                    WHERE entry_slug = ?"""
        query2 = "DELETE FROM entries WHERE entry_id = ?"
        query3 = "DELETE FROM revisions WHERE rev_entry = ?"
        try:
            slug = self._slugify(data.args[1])
        except IndexError:
            self.reply(data, "Please specify an entry to delete.")
            return

        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                id_, author = conn.execute(query1, (slug,)).fetchone()
            except (sqlite.OperationalError, TypeError):
                msg = "Entry \x0302{0}\x0F not found.".format(data.args[1])
                self.reply(data, msg)
                return
            permdb = self.config.irc["permissions"]
            if author != data.host and not permdb.is_admin(data):
                msg = "You must be an author or a bot admin to delete this entry."
                self.reply(data, msg)
                return
            conn.execute(query2, (id_,))
            conn.execute(query3, (id_,))

        self.reply(data, "Entry \x0302{0}\x0F deleted.".format(data.args[1]))

    def _slugify(self, name):
        """Convert *name* into an identifier for storing in the database."""
        return name.lower().replace("_", "").replace("-", "").decode("utf8")

    def _create_db(self, conn):
        """Initialize the notes database with its necessary tables."""
        script = """
            CREATE TABLE entries (entry_id, entry_slug, entry_title,
                                  entry_revision);
            CREATE TABLE users (user_id, user_host);
            CREATE TABLE revisions (rev_id, rev_entry, rev_user, rev_timestamp,
                                    rev_content);
        """
        conn.executescript(script)

    def _get_next_entry(self, conn):
        """Get the next entry ID."""
        query = "SELECT MAX(entry_id) FROM entries"
        later = conn.execute(query).fetchone()[0]
        return later + 1 if later else 1

    def _get_next_revision(self, conn):
        """Get the next revision ID."""
        query = "SELECT MAX(rev_id) FROM revisions"
        later = conn.execute(query).fetchone()[0]
        return later + 1 if later else 1

    def _get_user(self, conn, host):
        """Get the user ID corresponding to a hostname, or make one."""
        query1 = "SELECT user_id FROM users WHERE user_host = ?"
        query2 = "SELECT MAX(user_id) FROM users"
        query3 = "INSERT INTO users VALUES (?, ?)"
        user = conn.execute(query1, (host,)).fetchone()
        if user:
            return user[0]
        last = conn.execute(query2).fetchone()[0]
        later = last + 1 if last else 1
        conn.execute(query3, (later, host))
        return later
