# Copyright (C) 2009-2024 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from __future__ import annotations

__all__ = ["ExclusionsDB"]

import logging
import re
import sqlite3
import threading
import time
import typing
import urllib.parse

from earwigbot import exceptions

if typing.TYPE_CHECKING:
    from earwigbot.wiki.page import Page
    from earwigbot.wiki.site import Site
    from earwigbot.wiki.sitesdb import SitesDB

DEFAULT_SOURCES = {
    "all": [  # Applies to all, but located on enwiki
        "User:EarwigBot/Copyvios/Exclusions",
        "User:EranBot/Copyright/Blacklist",
    ],
    "enwiki": [
        "Wikipedia:Mirrors and forks/ABC",
        "Wikipedia:Mirrors and forks/DEF",
        "Wikipedia:Mirrors and forks/GHI",
        "Wikipedia:Mirrors and forks/JKL",
        "Wikipedia:Mirrors and forks/MNO",
        "Wikipedia:Mirrors and forks/PQR",
        "Wikipedia:Mirrors and forks/STU",
        "Wikipedia:Mirrors and forks/VWXYZ",
    ],
}

_RE_STRIP_PREFIX = r"^https?://(www\.)?"


class ExclusionsDB:
    """
    **EarwigBot: Wiki Toolset: Exclusions Database Manager**

    Controls the :file:`exclusions.db` file, which stores URLs excluded from copyright
    violation checks on account of being known mirrors, for example.
    """

    def __init__(self, sitesdb: SitesDB, dbfile: str, logger: logging.Logger) -> None:
        self._sitesdb = sitesdb
        self._dbfile = dbfile
        self._logger = logger
        self._db_access_lock = threading.Lock()

    def __repr__(self) -> str:
        """Return the canonical string representation of the ExclusionsDB."""
        return (
            f"ExclusionsDB(sitesdb={self._sitesdb!r}, dbfile={self._dbfile!r}, "
            f"logger={self._logger!r})"
        )

    def __str__(self) -> str:
        """Return a nice string representation of the ExclusionsDB."""
        return f"<ExclusionsDB at {self._dbfile}>"

    def _create(self) -> None:
        """Initialize the exclusions database with its necessary tables."""
        script = """
            CREATE TABLE sources (source_sitename, source_page);
            CREATE TABLE updates (update_sitename, update_time);
            CREATE TABLE exclusions (exclusion_sitename, exclusion_url);
        """
        query = "INSERT INTO sources VALUES (?, ?);"
        sources: list[tuple[str, str]] = []
        for sitename, pages in DEFAULT_SOURCES.items():
            for page in pages:
                sources.append((sitename, page))

        with sqlite3.connect(self._dbfile) as conn:
            conn.executescript(script)
            conn.executemany(query, sources)

    def _load_source(self, site: Site, source: str) -> set[str]:
        """Load from a specific source and return a set of URLs."""
        urls: set[str] = set()
        try:
            data = site.get_page(source, follow_redirects=True).get()
        except exceptions.PageNotFoundError:
            return urls

        if source == "User:EarwigBot/Copyvios/Exclusions":
            for line in data.splitlines():
                match = re.match(
                    r"^\s*url\s*=\s*(?:\<nowiki\>\s*)?(.+?)\s*(?:\</nowiki\>\s*)?(?:#.*?)?$",
                    line,
                )
                if match:
                    url = re.sub(_RE_STRIP_PREFIX, "", match.group(1))
                    if url:
                        urls.add(url)
            return urls

        if source == "User:EranBot/Copyright/Blacklist":
            for line in data.splitlines()[1:]:
                line = re.sub(r"(#|==).*$", "", line).strip()
                if line:
                    urls.add("re:" + line)
            return urls

        for line in data.splitlines():
            if re.match(r"^(\s*\|?\s*url\s*=)|(\*?\s*Site:)", line):
                for url in re.findall(r"(https?://.+?)(?:[ [\]<>{}()]|$)", line):
                    url = re.sub(_RE_STRIP_PREFIX, "", url)
                    if url:
                        urls.add(url)
        return urls

    def _update(self, sitename: str) -> None:
        """Update the database from listed sources in the index."""
        query1 = "SELECT source_page FROM sources WHERE source_sitename = ?"
        query2 = "SELECT exclusion_url FROM exclusions WHERE exclusion_sitename = ?"
        query3 = (
            "DELETE FROM exclusions WHERE exclusion_sitename = ? AND exclusion_url = ?"
        )
        query4 = "INSERT INTO exclusions VALUES (?, ?)"
        query5 = "SELECT 1 FROM updates WHERE update_sitename = ?"
        query6 = "UPDATE updates SET update_time = ? WHERE update_sitename = ?"
        query7 = "INSERT INTO updates VALUES (?, ?)"

        if sitename == "all":
            site = self._sitesdb.get_site("enwiki")
        else:
            site = self._sitesdb.get_site(sitename)
        with self._db_access_lock, sqlite3.connect(self._dbfile) as conn:
            urls: set[str] = set()
            for (source,) in conn.execute(query1, (sitename,)):
                urls |= self._load_source(site, source)
            for (url,) in conn.execute(query2, (sitename,)):
                if url in urls:
                    urls.remove(url)
                else:
                    conn.execute(query3, (sitename, url))
            conn.executemany(query4, [(sitename, url) for url in urls])
            if conn.execute(query5, (sitename,)).fetchone():
                conn.execute(query6, (int(time.time()), sitename))
            else:
                conn.execute(query7, (sitename, int(time.time())))

    def _get_last_update(self, sitename: str) -> int:
        """Return the UNIX timestamp of the last time the db was updated."""
        query = "SELECT update_time FROM updates WHERE update_sitename = ?"
        with self._db_access_lock, sqlite3.connect(self._dbfile) as conn:
            try:
                result = conn.execute(query, (sitename,)).fetchone()
            except sqlite3.OperationalError:
                self._create()
                return 0
            return result[0] if result else 0

    def sync(self, sitename: str, force: bool = False) -> None:
        """
        Update the database if it hasn't been updated recently.

        This updates the exclusions database for the site *sitename* and "all".

        Site-specific lists are considered stale after 48 hours; global lists after
        12 hours.
        """
        max_staleness = 60 * 60 * (12 if sitename == "all" else 48)
        time_since_update = int(time.time() - self._get_last_update(sitename))
        if force or time_since_update > max_staleness:
            self._logger.info(
                f"Updating stale database: {sitename} (last updated "
                f"{time_since_update} seconds ago)"
            )
            self._update(sitename)
        else:
            self._logger.debug(
                f"Database for {sitename} is still fresh (last updated "
                f"{time_since_update} seconds ago)"
            )
        if sitename != "all":
            self.sync("all", force=force)

    def check(self, sitename: str, url: str) -> bool:
        """
        Check whether a given URL is in the exclusions database.

        Return ``True`` if the URL is in the database, or ``False`` otherwise.
        """
        normalized = re.sub(_RE_STRIP_PREFIX, "", url.lower())
        parsed = urllib.parse.urlparse(url.lower())
        query = """SELECT exclusion_url FROM exclusions
                   WHERE exclusion_sitename = ? OR exclusion_sitename = ?"""
        with self._db_access_lock, sqlite3.connect(self._dbfile) as conn:
            for (excl,) in conn.execute(query, (sitename, "all")):
                excl = excl.lower()
                if excl.startswith("*."):
                    excl = excl[2:]
                    if "/" in excl:
                        excl_netloc, excl_path = excl.split("/", 1)
                    else:
                        excl_netloc, excl_path = excl, ""
                    matches = parsed.netloc == excl_netloc or (
                        parsed.netloc.endswith("." + excl_netloc)
                    )
                    if matches and excl_path:
                        matches = excl_path.startswith(parsed.path)
                elif excl.startswith("re:"):
                    try:
                        matches = re.match(excl[3:], normalized)
                    except re.error:
                        continue
                else:
                    matches = normalized.startswith(excl)
                if matches:
                    self._logger.debug(f"Exclusion detected in {sitename} for {url}")
                    return True

        self._logger.debug(f"No exclusions in {sitename} for {url}")
        return False

    def get_mirror_hints(self, page: Page, try_mobile: bool = True) -> list[str]:
        """
        Return a list of strings that indicate the existence of a mirror.

        The source parser checks for the presence of these strings inside of certain
        HTML tag attributes (``"href"`` and ``"src"``).
        """
        site = page.site
        path = urllib.parse.urlparse(page.url).path
        roots = [site.domain]
        scripts = ["index.php", "load.php", "api.php"]

        if try_mobile:
            fragments = re.search(r"^([\w]+)\.([\w]+).([\w]+)$", site.domain)
            if fragments:
                roots.append(f"{fragments[1]}.m.{fragments[2]}.{fragments[3]}")

        general = [
            root + site.script_path + "/" + script
            for root in roots
            for script in scripts
        ]
        specific = [root + path for root in roots]
        return general + specific
