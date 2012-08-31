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
import sqlite3 as sqlite
from threading import Lock
from time import time
from urlparse import urlparse

from earwigbot import exceptions

__all__ = ["ExclusionsDB"]

default_sources = {
    "enwiki": [
        "Wikipedia:Mirrors and forks/Abc", "Wikipedia:Mirrors and forks/Def",
        "Wikipedia:Mirrors and forks/Ghi", "Wikipedia:Mirrors and forks/Jkl",
        "Wikipedia:Mirrors and forks/Mno", "Wikipedia:Mirrors and forks/Pqr",
        "Wikipedia:Mirrors and forks/Stu", "Wikipedia:Mirrors and forks/Vwxyz",
        "User:EarwigBot/Copyvios/Exclusions"
    ]
}

class ExclusionsDB(object):
    """
    **EarwigBot: Wiki Toolset: Exclusions Database Manager**

    Controls the :file:`exclusions.db` file, which stores URLs excluded from
    copyright violation checks on account of being known mirrors, for example.
    """

    def __init__(self, sitesdb, dbfile, logger):
        self._sitesdb = sitesdb
        self._dbfile = dbfile
        self._logger = logger
        self._db_access_lock = Lock()

    def __repr__(self):
        """Return the canonical string representation of the ExclusionsDB."""
        res = "ExclusionsDB(sitesdb={0!r}, dbfile={1!r}, logger={2!r})"
        return res.format(self._sitesdb, self._dbfile, self._logger)

    def __str__(self):
        """Return a nice string representation of the ExclusionsDB."""
        return "<ExclusionsDB at {0}>".format(self._dbfile)

    def _create(self):
        """Initialize the exclusions database with its necessary tables."""
        script = """
            CREATE TABLE sources (source_sitename, source_page);
            CREATE TABLE updates (update_sitename, update_time);
            CREATE TABLE exclusions (exclusion_sitename, exclusion_url);
        """
        query = "INSERT INTO sources VALUES (?, ?);"
        sources = []
        for sitename, pages in default_sources.iteritems():
            [sources.append((sitename, page)) for page in pages]

        with sqlite.connect(self._dbfile) as conn:
            conn.executescript(script)
            conn.executemany(query, sources)

    def _load_source(self, site, source):
        """Load from a specific source and return a set of URLs."""
        urls = set()
        try:
            data = site.get_page(source).get()
        except exceptions.PageNotFoundError:
            return urls

        regexes = [
            "url\s*=\s*<nowiki>(?:https?:)?(?://)?(.*)</nowiki>",
            "\*\s*Site:\s*\[?(?:https?:)?(?://)?(.*)\]?"
        ]
        for regex in regexes:
            [urls.add(url.lower()) for (url,) in re.findall(regex, data, re.I)]
        return urls

    def _update(self, sitename):
        """Update the database from listed sources in the index."""
        query1 = "SELECT source_page FROM sources WHERE source_sitename = ?;"
        query2 = "SELECT exclusion_url FROM exclusions WHERE exclusion_sitename = ?"
        query3 = "DELETE FROM exclusions WHERE exclusion_sitename = ? AND exclusion_url = ?"
        query4 = "INSERT INTO exclusions VALUES (?, ?);"
        query5 = "SELECT 1 FROM updates WHERE update_sitename = ?;"
        query6 = "UPDATE updates SET update_time = ? WHERE update_sitename = ?;"
        query7 = "INSERT INTO updates VALUES (?, ?);"

        site = self._sitesdb.get_site(sitename)
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            urls = set()
            for (source,) in conn.execute(query1, (sitename,)):
                urls |= self._load_source(site, source)
            for (url,) in conn.execute(query2, (sitename,)):
                if url in urls:
                    urls.remove(url)
                else:
                    conn.execute(query3, (sitename, url))
            conn.executemany(query4, [(sitename, url) for url in urls])
            if conn.execute(query5, (sitename,)).fetchone():
                conn.execute(query6, (int(time()), sitename))
            else:
                conn.execute(query7, (sitename, int(time())))

    def _get_last_update(self, sitename):
        """Return the UNIX timestamp of the last time the db was updated."""
        query = "SELECT update_time FROM updates WHERE update_sitename = ?;"
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            try:
                result = conn.execute(query, (sitename,)).fetchone()
            except sqlite.OperationalError:
                self._create()
                return 0
            return result[0] if result else 0

    def sync(self, sitename):
        """Update the database if it hasn't been updated in the past week.

        This only updates the exclusions database for the *sitename* site.
        """
        max_staleness = 60 * 60 * 24 * 7
        time_since_update = int(time() - self._get_last_update(sitename))
        if time_since_update > max_staleness:
            log = u"Updating stale database: {0} (last updated {1} seconds ago)"
            self._logger.info(log.format(sitename, time_since_update))
            self._update(sitename)
        else:
            log = u"Database for {0} is still fresh (last updated {1} seconds ago)"
            self._logger.debug(log.format(sitename, time_since_update))

    def check(self, sitename, url):
        """Check whether a given URL is in the exclusions database.

        Return ``True`` if the URL is in the database, or ``False`` otherwise.
        """
        normalized = re.sub("https?://", "", url.lower())
        query = "SELECT exclusion_url FROM exclusions WHERE exclusion_sitename = ?"
        with sqlite.connect(self._dbfile) as conn, self._db_access_lock:
            for (excl,) in conn.execute(query, (sitename,)):
                if excl.startswith("*."):
                    netloc = urlparse(url.lower()).netloc
                    matches = True if excl[2:] in netloc else False
                else:
                    matches = True if normalized.startswith(excl) else False
                if matches:
                    log = u"Exclusion detected in {0} for {1}"
                    self._logger.debug(log.format(sitename, url))
                    return True

        log = u"No exclusions in {0} for {1}".format(sitename, url)
        self._logger.debug(log)
        return False
