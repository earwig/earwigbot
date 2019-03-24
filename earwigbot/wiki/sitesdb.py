# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2019 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from collections import OrderedDict
from cookielib import LWPCookieJar, LoadError
import errno
from os import chmod, path
from platform import python_version
import stat
import sqlite3 as sqlite

from earwigbot import __version__
from earwigbot.exceptions import SiteNotFoundError
from earwigbot.wiki.copyvios.exclusions import ExclusionsDB
from earwigbot.wiki.site import Site

__all__ = ["SitesDB"]

class SitesDB(object):
    """
    **EarwigBot: Wiki Toolset: Sites Database Manager**

    This class controls the :file:`sites.db` file, which stores information
    about all wiki sites known to the bot. Three public methods act as bridges
    between the bot's config files and :py:class:`~earwigbot.wiki.site.Site`
    objects:

    - :py:meth:`get_site`:    returns a Site object corresponding to a site
    - :py:meth:`add_site`:    stores a site in the database
    - :py:meth:`remove_site`: removes a site from the database

    There's usually no need to use this class directly. All public methods
    here are available as :py:meth:`bot.wiki.get_site`,
    :py:meth:`bot.wiki.add_site`, and :py:meth:`bot.wiki.remove_site`, which
    use a :file:`sites.db` file located in the same directory as our
    :file:`config.yml` file. Lower-level access can be achieved by importing
    the manager class (``from earwigbot.wiki import SitesDB``).
    """

    def __init__(self, bot):
        """Set up the manager with an attribute for the base Bot object."""
        self.config = bot.config
        self._logger = bot.logger.getChild("wiki")

        self._sites = {}  # Internal site cache
        self._sitesdb = path.join(bot.config.root_dir, "sites.db")
        self._cookie_file = path.join(bot.config.root_dir, ".cookies")
        self._cookiejar = None

        excl_db = path.join(bot.config.root_dir, "exclusions.db")
        excl_logger = self._logger.getChild("exclusionsdb")
        self._exclusions_db = ExclusionsDB(self, excl_db, excl_logger)

    def __repr__(self):
        """Return the canonical string representation of the SitesDB."""
        res = "SitesDB(config={0!r}, sitesdb={1!r}, cookie_file={2!r})"
        return res.format(self.config, self._sitesdb, self._cookie_file)

    def __str__(self):
        """Return a nice string representation of the SitesDB."""
        return "<SitesDB at {0}>".format(self._sitesdb)

    def _get_cookiejar(self):
        """Return a LWPCookieJar object loaded from our .cookies file.

        The same .cookies file is returned every time, located in the project
        root, same directory as config.yml and bot.py. If it doesn't exist, we
        will create the file and set it to be readable and writeable only by
        us. If it exists but the information inside is bogus, we'll ignore it.

        This is normally called by _make_site_object() (in turn called by
        get_site()), and the cookiejar is passed to our Site's constructor,
        used when it makes API queries. This way, we can easily preserve
        cookies between sites (e.g., for CentralAuth), making logins easier.
        """
        if self._cookiejar:
            return self._cookiejar

        self._cookiejar = LWPCookieJar(self._cookie_file)

        try:
            self._cookiejar.load()
        except LoadError:
            pass  # File contains bad data, so ignore it completely
        except IOError as e:
            if e.errno == errno.ENOENT:  # "No such file or directory"
                # Create the file and restrict reading/writing only to the
                # owner, so others can't peak at our cookies:
                open(self._cookie_file, "w").close()
                chmod(self._cookie_file, stat.S_IRUSR|stat.S_IWUSR)
            else:
                raise

        return self._cookiejar

    def _create_sitesdb(self):
        """Initialize the sitesdb file with its three necessary tables."""
        script = """
        CREATE TABLE sites (site_name, site_project, site_lang, site_base_url,
                            site_article_path, site_script_path);
        CREATE TABLE sql_data (sql_site, sql_data_key, sql_data_value);
        CREATE TABLE namespaces (ns_site, ns_id, ns_name, ns_is_primary_name);
        """
        with sqlite.connect(self._sitesdb) as conn:
            conn.executescript(script)

    def _get_site_object(self, name):
        """Return the site from our cache, or create it if it doesn't exist.

        This is essentially just a wrapper around _make_site_object that
        returns the same object each time a specific site is asked for.
        """
        try:
            return self._sites[name]
        except KeyError:
            site = self._make_site_object(name)
            self._sites[name] = site
            return site

    def _load_site_from_sitesdb(self, name):
        """Return all information stored in the sitesdb relating to given site.

        The information will be returned as a tuple, containing the site's
        name, project, language, base URL, article path, script path, SQL
        connection data, and namespaces, in that order. If the site is not
        found in the database, SiteNotFoundError will be raised. An empty
        database will be created before the exception is raised if none exists.
        """
        query1 = "SELECT * FROM sites WHERE site_name = ?"
        query2 = "SELECT sql_data_key, sql_data_value FROM sql_data WHERE sql_site = ?"
        query3 = "SELECT ns_id, ns_name, ns_is_primary_name FROM namespaces WHERE ns_site = ?"
        error = "Site '{0}' not found in the sitesdb.".format(name)
        with sqlite.connect(self._sitesdb) as conn:
            try:
                site_data = conn.execute(query1, (name,)).fetchone()
            except sqlite.OperationalError:
                self._create_sitesdb()
                raise SiteNotFoundError(error)
            if not site_data:
                raise SiteNotFoundError(error)
            sql_data = conn.execute(query2, (name,)).fetchall()
            ns_data = conn.execute(query3, (name,)).fetchall()

        name, project, lang, base_url, article_path, script_path = site_data
        sql = dict(sql_data)
        namespaces = {}
        for ns_id, ns_name, ns_is_primary_name in ns_data:
            try:
                if ns_is_primary_name:  # "Primary" name goes first in list
                    namespaces[ns_id].insert(0, ns_name)
                else:  # Ordering of the aliases doesn't matter
                    namespaces[ns_id].append(ns_name)
            except KeyError:
                namespaces[ns_id] = [ns_name]

        return (name, project, lang, base_url, article_path, script_path, sql,
                namespaces)

    def _make_site_object(self, name):
        """Return a Site object associated with the site *name* in our sitesdb.

        This calls _load_site_from_sitesdb(), so SiteNotFoundError will be
        raised if the site is not in our sitesdb.
        """
        cookiejar = self._get_cookiejar()
        (name, project, lang, base_url, article_path, script_path, sql,
         namespaces) = self._load_site_from_sitesdb(name)

        config = self.config
        login = (config.wiki.get("username"), config.wiki.get("password"))
        oauth = config.wiki.get("oauth")
        user_agent = config.wiki.get("userAgent")
        use_https = config.wiki.get("useHTTPS", True)
        assert_edit = config.wiki.get("assert")
        maxlag = config.wiki.get("maxlag")
        wait_between_queries = config.wiki.get("waitTime", 2)
        logger = self._logger.getChild(name)
        search_config = config.wiki.get("search", OrderedDict()).copy()

        if user_agent:
            user_agent = user_agent.replace("$1", __version__)
            user_agent = user_agent.replace("$2", python_version())

        if search_config:
            nltk_dir = path.join(self.config.root_dir, ".nltk")
            search_config["nltk_dir"] = nltk_dir
            search_config["exclusions_db"] = self._exclusions_db

        if not sql:
            sql = config.wiki.get("sql", OrderedDict()).copy()
            for key, value in sql.iteritems():
                if isinstance(value, basestring) and "$1" in value:
                    sql[key] = value.replace("$1", name)

        return Site(name=name, project=project, lang=lang, base_url=base_url,
                    article_path=article_path, script_path=script_path,
                    sql=sql, namespaces=namespaces, login=login, oauth=oauth,
                    cookiejar=cookiejar, user_agent=user_agent,
                    use_https=use_https, assert_edit=assert_edit,
                    maxlag=maxlag, wait_between_queries=wait_between_queries,
                    logger=logger, search_config=search_config)

    def _get_site_name_from_sitesdb(self, project, lang):
        """Return the name of the first site with the given project and lang.

        If we can't find the site with the given information, we'll also try
        searching for a site whose base_url contains "{lang}.{project}". There
        are a few sites, like the French Wikipedia, that set their project to
        something other than the expected "wikipedia" ("wikipédia" in this
        case), but we should correctly find them when doing get_site(lang="fr",
        project="wikipedia").

        If the site is not found, return None. An empty sitesdb will be created
        if none exists.
        """
        query1 = "SELECT site_name FROM sites WHERE site_project = ? and site_lang = ?"
        query2 = "SELECT site_name FROM sites WHERE site_base_url LIKE ?"
        with sqlite.connect(self._sitesdb) as conn:
            try:
                site = conn.execute(query1, (project, lang)).fetchone()
                if site:
                    return site[0]
                else:
                    url = "//{0}.{1}.%".format(lang, project)
                    site = conn.execute(query2, (url,)).fetchone()
                    return site[0] if site else None
            except sqlite.OperationalError:
                self._create_sitesdb()

    def _add_site_to_sitesdb(self, site):
        """Extract relevant info from a Site object and add it to the sitesdb.

        Works like a reverse _load_site_from_sitesdb(); the site's project,
        language, base URL, article path, script path, SQL connection data, and
        namespaces are extracted from the site and inserted into the sites
        database. If the sitesdb doesn't exist, we'll create it first.
        """
        name = site.name
        sites_data = (name, site.project, site.lang, site._base_url,
                      site._article_path, site._script_path)
        sql_data = [(name, key, val) for key, val in site._sql_data.iteritems()]
        ns_data = []
        for ns_id, ns_names in site._namespaces.iteritems():
            ns_data.append((name, ns_id, ns_names.pop(0), True))
            for ns_name in ns_names:
                ns_data.append((name, ns_id, ns_name, False))

        with sqlite.connect(self._sitesdb) as conn:
            check_exists = "SELECT 1 FROM sites WHERE site_name = ?"
            try:
                exists = conn.execute(check_exists, (name,)).fetchone()
            except sqlite.OperationalError:
                self._create_sitesdb()
            else:
                if exists:
                    conn.execute("DELETE FROM sites WHERE site_name = ?", (name,))
                    conn.execute("DELETE FROM sql_data WHERE sql_site = ?", (name,))
                    conn.execute("DELETE FROM namespaces WHERE ns_site = ?", (name,))
            conn.execute("INSERT INTO sites VALUES (?, ?, ?, ?, ?, ?)", sites_data)
            conn.executemany("INSERT INTO sql_data VALUES (?, ?, ?)", sql_data)
            conn.executemany("INSERT INTO namespaces VALUES (?, ?, ?, ?)", ns_data)

    def _remove_site_from_sitesdb(self, name):
        """Remove a site by name from the sitesdb and the internal cache."""
        try:
            del self._sites[name]
        except KeyError:
            pass

        with sqlite.connect(self._sitesdb) as conn:
            cursor = conn.execute("DELETE FROM sites WHERE site_name = ?", (name,))
            if cursor.rowcount == 0:
                return False
            else:
                conn.execute("DELETE FROM sql_data WHERE sql_site = ?", (name,))
                conn.execute("DELETE FROM namespaces WHERE ns_site = ?", (name,))
                self._logger.info("Removed site '{0}'".format(name))
                return True

    def get_site(self, name=None, project=None, lang=None):
        """Return a Site instance based on information from the sitesdb.

        With no arguments, return the default site as specified by our config
        file. This is ``config.wiki["defaultSite"]``.

        With *name* specified, return the site with that name. This is
        equivalent to the site's ``wikiid`` in the API, like *enwiki*.

        With *project* and *lang* specified, return the site whose project and
        language match these values. If there are multiple sites with the same
        values (unlikely), this is not a reliable way of loading a site. Call
        the function with an explicit *name* in that case.

        We will attempt to login to the site automatically using
        ``config.wiki["username"]`` and ``config.wiki["password"]`` if both are
        defined.

        Specifying a project without a lang or a lang without a project will
        raise :py:exc:`TypeError`. If all three args are specified, *name* will
        be first tried, then *project* and *lang* if *name* doesn't work. If a
        site cannot be found in the sitesdb,
        :py:exc:`~earwigbot.exceptions.SiteNotFoundError` will be raised. An
        empty sitesdb will be created if none is found.
        """
        # Someone specified a project without a lang, or vice versa:
        if (project and not lang) or (not project and lang):
            e = "Keyword arguments 'lang' and 'project' must be specified together."
            raise TypeError(e)

        # No args given, so return our default site:
        if not name and not project and not lang:
            try:
                default = self.config.wiki["defaultSite"]
            except KeyError:
                e = "Default site is not specified in config."
                raise SiteNotFoundError(e)
            return self._get_site_object(default)

        # Name arg given, but don't look at others unless `name` isn't found:
        if name:
            try:
                return self._get_site_object(name)
            except SiteNotFoundError:
                if project and lang:
                    name = self._get_site_name_from_sitesdb(project, lang)
                    if name:
                        return self._get_site_object(name)
                raise

        # If we end up here, then project and lang are the only args given:
        name = self._get_site_name_from_sitesdb(project, lang)
        if name:
            return self._get_site_object(name)
        e = "Site '{0}:{1}' not found in the sitesdb.".format(project, lang)
        raise SiteNotFoundError(e)

    def add_site(self, project=None, lang=None, base_url=None,
                 script_path="/w", sql=None):
        """Add a site to the sitesdb so it can be retrieved with get_site().

        If only a project and a lang are given, we'll guess the *base_url* as
        ``"//{lang}.{project}.org"`` (which is protocol-relative, becoming
        ``"https"`` if *useHTTPS* is ``True`` in config otherwise ``"http"``).
        If this is wrong, provide the correct *base_url* as an argument (in
        which case project and lang are ignored). Most wikis use ``"/w"`` as
        the script path (meaning the API is located at
        ``"{base_url}{script_path}/api.php"`` ->
        ``"//{lang}.{project}.org/w/api.php"``), so this is the default. If
        your wiki is different, provide the script_path as an argument. SQL
        connection settings are guessed automatically using config's template
        value. If this is wrong or not specified, provide a dict of kwargs as
        *sql* and Site will pass it to :py:func:`oursql.connect(**sql)
        <oursql.connect>`, allowing you to make queries with
        :py:meth:`site.sql_query <earwigbot.wiki.site.Site.sql_query>`.

        Returns ``True`` if the site was added successfully or ``False`` if the
        site is already in our sitesdb (this can be done purposefully to update
        old site info). Raises :py:exc:`~earwigbot.exception.SiteNotFoundError`
        if not enough information has been provided to identify the site (e.g.
        a *project* but not a *lang*).
        """
        if not base_url:
            if not project or not lang:
                e = "Without a base_url, both a project and a lang must be given."
                raise SiteNotFoundError(e)
            base_url = "//{0}.{1}.org".format(lang, project)
        cookiejar = self._get_cookiejar()

        config = self.config
        login = (config.wiki.get("username"), config.wiki.get("password"))
        oauth = config.wiki.get("oauth")
        user_agent = config.wiki.get("userAgent")
        use_https = config.wiki.get("useHTTPS", True)
        assert_edit = config.wiki.get("assert")
        maxlag = config.wiki.get("maxlag")
        wait_between_queries = config.wiki.get("waitTime", 2)

        if user_agent:
            user_agent = user_agent.replace("$1", __version__)
            user_agent = user_agent.replace("$2", python_version())

        # Create a Site object to log in and load the other attributes:
        site = Site(base_url=base_url, script_path=script_path, sql=sql,
                    login=login, oauth=oauth, cookiejar=cookiejar,
                    user_agent=user_agent, use_https=use_https,
                    assert_edit=assert_edit, maxlag=maxlag,
                    wait_between_queries=wait_between_queries)

        self._logger.info("Added site '{0}'".format(site.name))
        self._add_site_to_sitesdb(site)
        return self._get_site_object(site.name)

    def remove_site(self, name=None, project=None, lang=None):
        """Remove a site from the sitesdb.

        Returns ``True`` if the site was removed successfully or ``False`` if
        the site was not in our sitesdb originally. If all three args (*name*,
        *project*, and *lang*) are given, we'll first try *name* and then try
        the latter two if *name* wasn't found in the database. Raises
        :py:exc:`TypeError` if a project was given but not a language, or vice
        versa. Will create an empty sitesdb if none was found.
        """
        # Someone specified a project without a lang, or vice versa:
        if (project and not lang) or (not project and lang):
            e = "Keyword arguments 'lang' and 'project' must be specified together."
            raise TypeError(e)

        if name:
            was_removed = self._remove_site_from_sitesdb(name)
            if not was_removed:
                if project and lang:
                    name = self._get_site_name_from_sitesdb(project, lang)
                    if name:
                        return self._remove_site_from_sitesdb(name)
            return was_removed

        if project and lang:
            name = self._get_site_name_from_sitesdb(project, lang)
            if name:
                return self._remove_site_from_sitesdb(name)

        return False
