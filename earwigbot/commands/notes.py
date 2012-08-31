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
            "rename": self.do_rename,
            "delete": self.do_delete,
            "info": self.do_info,
        }

        if not data.args:
            msg = "The Earwig Mini-Wiki: running v{0}. Subcommands are: {1}. You can get help on any with '!{2} help subcommand'."
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
            CREATE TABLE pages (page_id, page_title);
            CREATE TABLE users (user_id, user_name);
            CREATE TABLE revisions (rev_id, rev_page, rev_user, rev_content);
        """
        conn.executescript(script)

    def do_list(self):
        pass

    def do_read(self):
        pass

    def edit(self):
        pass

    def rename(self):
        pass

    def delete(self):
        pass

    def info(self):
        pass

