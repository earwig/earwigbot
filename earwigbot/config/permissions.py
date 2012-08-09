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

import sqlite3 as sqlite
from threading import Lock

__all__ = ["PermissionsDB"]

class PermissionsDB(object):
    def __init__(self, dbfile):
        self._dbfile = dbfile
        self._db_access_lock = Lock()
        self._data = {}

    def __repr__(self):
        """Return the canonical string representation of the PermissionsDB."""
        res = "PermissionsDB(dbfile={0!r})"
        return res.format(self._dbfile)

    def __str__(self):
        """Return a nice string representation of the PermissionsDB."""
        return "<PermissionsDB at {0}>".format(self._dbfile)

    def _create(self, conn):
        """Initialize the permissions database with its necessary tables."""
        query = """CREATE TABLE users (user_nick, user_ident, user_host,
                                       user_rank)"""
        conn.execute(query)

    def load(self):
        """Load permissions from an existing database, or create a new one."""
        query = "SELECT user_nick, user_ident, user_host, user_rank FROM users"
        self._data = {}
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                for nick, ident, host, rank in conn.execute(query):
                    try:
                        self._data[rank].append(_User(nick, ident, host))
                    except KeyError:
                        self._data[rank] = [_User(nick, ident, host)]
            except sqlite.OperationalError:
                self._create(conn)


class _User(object):
    def __init__(self, nick, ident, host):
        self.nick = nick
        self.ident = ident
        self.host = host
