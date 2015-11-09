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

from fnmatch import fnmatch
import sqlite3 as sqlite
from threading import Lock

__all__ = ["PermissionsDB"]

class PermissionsDB(object):
    """
    **EarwigBot: Permissions Database Manager**

    Controls the :file:`permissions.db` file, which stores the bot's owners and
    admins for the purposes of using certain dangerous IRC commands.
    """
    ADMIN = 1
    OWNER = 2

    def __init__(self, dbfile):
        self._dbfile = dbfile
        self._db_access_lock = Lock()
        self._users = {}
        self._attributes = {}

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
                                       user_rank);
                   CREATE TABLE attributes (attr_uid, attr_key, attr_value);"""
        conn.executescript(query)

    def _is_rank(self, user, rank):
        """Return True if the given user has the given rank, else False."""
        try:
            for rule in self._users[rank]:
                if user in rule:
                    return rule
        except KeyError:
            pass
        return False

    def _set_rank(self, user, rank):
        """Add a User to the database under a given rank."""
        query = "INSERT INTO users VALUES (?, ?, ?, ?)"
        with self._db_access_lock:
            with sqlite.connect(self._dbfile) as conn:
                conn.execute(query, (user.nick, user.ident, user.host, rank))
            try:
                self._users[rank].append(user)
            except KeyError:
                self._users[rank] = [user]
        return user

    def _del_rank(self, user, rank):
        """Remove a User from the database."""
        query = """DELETE FROM users WHERE user_nick = ? AND user_ident = ? AND
                                           user_host = ? AND user_rank = ?"""
        with self._db_access_lock:
            try:
                for rule in self._users[rank]:
                    if user in rule:
                        with sqlite.connect(self._dbfile) as conn:
                            args = (user.nick, user.ident, user.host, rank)
                            conn.execute(query, args)
                        self._users[rank].remove(rule)
                        return rule
            except KeyError:
                pass
        return None

    @property
    def users(self):
        """A dict of all users in the permissions database."""
        return self._users

    @property
    def attributes(self):
        """A dict of all attributes in the permissions database."""
        return self._attributes

    def load(self):
        """Load permissions from an existing database, or create a new one."""
        qry1 = "SELECT user_nick, user_ident, user_host, user_rank FROM users"
        qry2 = "SELECT attr_uid, attr_key, attr_value FROM attributes"
        self._users = {}
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                for nick, ident, host, rank in conn.execute(qry1):
                    try:
                        self._users[rank].append(_User(nick, ident, host))
                    except KeyError:
                        self._users[rank] = [_User(nick, ident, host)]
                for user, key, value in conn.execute(qry2):
                    try:
                        self._attributes[user][key] = value
                    except KeyError:
                        self._attributes[user] = {key: value}
            except sqlite.OperationalError:
                self._create(conn)

    def has_exact(self, rank, nick="*", ident="*", host="*"):
        """Return ``True`` if there is an exact match for this rule."""
        try:
            for usr in self._users[rank]:
                if nick != usr.nick or ident != usr.ident or host != usr.host:
                    continue
                return usr
        except KeyError:
            pass
        return False

    def is_admin(self, data):
        """Return ``True`` if the given user is a bot admin, else ``False``."""
        user = _User(data.nick, data.ident, data.host)
        return self._is_rank(user, rank=self.ADMIN)

    def is_owner(self, data):
        """Return ``True`` if the given user is a bot owner, else ``False``."""
        user = _User(data.nick, data.ident, data.host)
        return self._is_rank(user, rank=self.OWNER)

    def add_admin(self, nick="*", ident="*", host="*"):
        """Add a nick/ident/host combo to the bot admins list."""
        return self._set_rank(_User(nick, ident, host), rank=self.ADMIN)

    def add_owner(self, nick="*", ident="*", host="*"):
        """Add a nick/ident/host combo to the bot owners list."""
        return self._set_rank(_User(nick, ident, host), rank=self.OWNER)

    def remove_admin(self, nick="*", ident="*", host="*"):
        """Remove a nick/ident/host combo to the bot admins list."""
        return self._del_rank(_User(nick, ident, host), rank=self.ADMIN)

    def remove_owner(self, nick="*", ident="*", host="*"):
        """Remove a nick/ident/host combo to the bot owners list."""
        return self._del_rank(_User(nick, ident, host), rank=self.OWNER)

    def has_attr(self, user, key):
        """Return ``True`` if a given user has a certain attribute, *key*."""
        return user in self._attributes and key in self._attributes[user]

    def get_attr(self, user, key):
        """Get the value of the attribute *key* of a given *user*.

        Raises :py:exc:`KeyError` if the *key* or *user* is not found.
        """
        return self._attributes[user][key]

    def set_attr(self, user, key, value):
        """Set the *value* of the attribute *key* of a given *user*."""
        query1 = """SELECT attr_value FROM attributes WHERE attr_uid = ?
                    AND attr_key = ?"""
        query2 = "INSERT INTO attributes VALUES (?, ?, ?)"
        query3 = """UPDATE attributes SET attr_value = ? WHERE attr_uid = ?
                    AND attr_key = ?"""
        with self._db_access_lock, sqlite.connect(self._dbfile) as conn:
            if conn.execute(query1, (user, key)).fetchone():
                conn.execute(query3, (value, user, key))
            else:
                conn.execute(query2, (user, key, value))
        try:
            self._attributes[user][key] = value
        except KeyError:
            self.attributes[user] = {key: value}

    def remove_attr(self, user, key):
        """Remove the attribute *key* of a given *user*."""
        query = "DELETE FROM attributes WHERE attr_uid = ? AND attr_key = ?"
        with self._db_access_lock, sqlite.connect(self._dbfile) as conn:
            conn.execute(query, (user, key))

class _User(object):
    """A class that represents an IRC user for the purpose of testing rules."""
    def __init__(self, nick, ident, host):
        self.nick = nick
        self.ident = ident
        self.host = host

    def __repr__(self):
        """Return the canonical string representation of the User."""
        res = "_User(nick={0!r}, ident={1!r}, host={2!r})"
        return res.format(self.nick, self.ident, self.host)

    def __str__(self):
        """Return a nice string representation of the User."""
        return "{0}!{1}@{2}".format(self.nick, self.ident, self.host)

    def __contains__(self, user):
        if fnmatch(user.nick, self.nick):
            if fnmatch(user.ident, self.ident):
                if fnmatch(user.host, self.host):
                    return True
        return False
