# -*- coding: utf-8  -*-

from cookielib import CookieJar
from gzip import GzipFile
from json import loads
from os.path import expanduser
from re import escape as re_escape, match as re_match
from StringIO import StringIO
from time import sleep
from urllib import unquote_plus, urlencode
from urllib2 import build_opener, HTTPCookieProcessor, URLError
from urlparse import urlparse

try:
    import oursql
except ImportError:
    oursql = None

from wiki.category import Category
from wiki.constants import *
from wiki.exceptions import *
from wiki.page import Page
from wiki.user import User

class Site(object):
    """
    EarwigBot's Wiki Toolset: Site Class

    Represents a Site, with support for API queries and returning Pages, Users,
    and Categories. The constructor takes a bunch of arguments and you probably
    won't need to call it directly, rather tools.get_site() for returning Site
    instances, tools.add_site() for adding new ones to config, and
    tools.del_site() for removing old ones from config, should suffice.

    Public methods:
    name                 -- returns our name (or "wikiid"), like "enwiki"
    project              -- returns our project name, like "wikipedia"
    lang                 -- returns our language code, like "en"
    domain               -- returns our web domain, like "en.wikipedia.org"
    api_query            -- does an API query with the given kwargs as params
    sql_query            -- does an SQL query and yields its results
    get_replag           -- returns the estimated database replication lag
    namespace_id_to_name -- given a namespace ID, returns associated name(s)
    namespace_name_to_id -- given a namespace name, returns associated id
    get_page             -- returns a Page object for the given title
    get_category         -- returns a Category object for the given title
    get_user             -- returns a User object for the given username
    """

    def __init__(self, name=None, project=None, lang=None, base_url=None,
                 article_path=None, script_path=None, sql=None,
                 namespaces=None, login=(None, None), cookiejar=None,
                 user_agent=None, assert_edit=None, maxlag=None):
        """Constructor for new Site instances.

        This probably isn't necessary to call yourself unless you're building a
        Site that's not in your config and you don't want to add it - normally
        all you need is tools.get_site(name), which creates the Site for you
        based on your config file. We accept a bunch of kwargs, but the only
        ones you really "need" are `base_url` and `script_path` - this is
        enough to figure out an API url. `login`, a tuple of
        (username, password), is highly recommended. `cookiejar` will be used
        to store cookies, and we'll use a normal CookieJar if none is given.

        First, we'll store the given arguments as attributes, then set up our
        URL opener. We'll load any of the attributes that weren't given from
        the API, and then log in if a username/pass was given and we aren't
        already logged in.
        """
        # Attributes referring to site information, filled in by an API query
        # if they are missing (and an API url can be determined):
        self._name = name
        self._project = project
        self._lang = lang
        self._base_url = base_url
        self._article_path = article_path
        self._script_path = script_path
        self._namespaces = namespaces

        # Attributes used for API queries: 
        self._assert_edit = assert_edit
        self._maxlag = maxlag
        self._max_retries = 5

        # Attributes used for SQL queries:
        self._sql_data = sql
        self._sql_conn = None

        # Set up cookiejar and URL opener for making API queries:
        if cookiejar is not None:
            self._cookiejar = cookiejar
        else:
            self._cookiejar = CookieJar()
        if user_agent is None:
            user_agent = USER_AGENT  # Set default UA from wiki.constants
        self._opener = build_opener(HTTPCookieProcessor(self._cookiejar))
        self._opener.addheaders = [("User-Agent", user_agent),
                                   ("Accept-Encoding", "gzip")]

        # Get all of the above attributes that were not specified as arguments:
        self._load_attributes()

        # If we have a name/pass and the API says we're not logged in, log in:
        self._login_info = name, password = login
        if name is not None and password is not None:
            logged_in_as = self._get_username_from_cookies()
            if logged_in_as is None or name != logged_in_as:
                self._login(login)

    def __repr__(self):
        """Returns the canonical string representation of the Site."""
        res = ", ".join((
            "Site(name={_name!r}", "project={_project!r}", "lang={_lang!r}",
            "base_url={_base_url!r}", "article_path={_article_path!r}",
            "script_path={_script_path!r}", "assert_edit={_assert_edit!r}",
            "maxlag={_maxlag!r}", "sql={_sql!r}", "login={0}",
            "user_agent={2!r}", "cookiejar={1})"
        ))
        name, password = self._login_info
        login = "({0}, {1})".format(repr(name), "hidden" if password else None)
        cookies = self._cookiejar.__class__.__name__
        try:
            cookies += "({0!r})".format(self._cookiejar.filename)
        except AttributeError:
            cookies += "()"
        agent = self._opener.addheaders[0][1]
        return res.format(login, cookies, agent, **self.__dict__)

    def __str__(self):
        """Returns a nice string representation of the Site."""
        res = "<Site {0} ({1}:{2}) at {3}>"
        return res.format(self.name(), self.project(), self.lang(),
                          self.domain())

    def _api_query(self, params, tries=0, wait=5):
        """Do an API query with `params` as a dict of parameters.

        This will first attempt to construct an API url from self._base_url and
        self._script_path. We need both of these, or else we'll raise
        SiteAPIError.

        We'll encode the given params, adding format=json along the way, as
        well as &assert= and &maxlag= based on self._assert_edit and _maxlag.
        We make the request through self._opener, which has built-in cookie
        support via self._cookiejar, a User-Agent (wiki.constants.USER_AGENT),
        and Accept-Encoding set to "gzip".

        Assuming everything went well, we'll gunzip the data (if compressed),
        load it as a JSON object, and return it.

        If our request failed for some reason, we'll raise SiteAPIError with
        details. If that reason was due to maxlag, we'll sleep for a bit and
        then repeat the query until we exceed self._max_retries.

        There's helpful MediaWiki API documentation at
        <http://www.mediawiki.org/wiki/API>.
        """
        if self._base_url is None or self._script_path is None:
            e = "Tried to do an API query, but no API URL is known."
            raise SiteAPIError(e)

        url = ''.join((self._base_url, self._script_path, "/api.php"))

        params["format"] = "json"  # This is the only format we understand
        if self._assert_edit:  # If requested, ensure that we're logged in
            params["assert"] = self._assert_edit
        if self._maxlag:  # If requested, don't overload the servers
            params["maxlag"] = self._maxlag

        data = urlencode(params)

        print url, data  # debug code

        try:
            response = self._opener.open(url, data)
        except URLError as error:
            if hasattr(error, "reason"):
                e = "API query failed: {0}.".format(error.reason)
            elif hasattr(error, "code"):
                e = "API query failed: got an error code of {0}."
                e = e.format(error.code)
            else:
                e = "API query failed."
            raise SiteAPIError(e)

        result = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(result)
            gzipper = GzipFile(fileobj=stream)
            result = gzipper.read()

        try:
            res = loads(result)  # Parse as a JSON object
        except ValueError:
            e = "API query failed: JSON could not be decoded."
            raise SiteAPIError(e)

        try:
            code = res["error"]["code"]
            info = res["error"]["info"]
        except (TypeError, KeyError):
            return res

        if code == "maxlag":
            if tries >= self._max_retries:
                e = "Maximum number of retries reached ({0})."
                raise SiteAPIError(e.format(self._max_retries))
            tries += 1
            msg = 'Server says: "{0}". Retrying in {1} seconds ({2}/{3}).'
            print msg.format(info, wait, tries, self._max_retries)
            sleep(wait)
            return self._api_query(params, tries=tries, wait=wait*3)
        else:
            e = 'API query failed: got error "{0}"; server says: "{1}".'
            error = SiteAPIError(e.format(code, info))
            error.code, error.info = code, info
            raise error

    def _load_attributes(self, force=False):
        """Load data about our Site from the API.

        This function is called by __init__() when one of the site attributes
        was not given as a keyword argument. We'll do an API query to get the
        missing data, but only if there actually *is* missing data.

        Additionally, you can call this with `force=True` to forcibly reload
        all attributes.
        """
        # All attributes to be loaded, except _namespaces, which is a special
        # case because it requires additional params in the API query:
        attrs = [self._name, self._project, self._lang, self._base_url,
            self._article_path, self._script_path]

        params = {"action": "query", "meta": "siteinfo"}

        if not self._namespaces or force:
            params["siprop"] = "general|namespaces|namespacealiases"
            result = self._api_query(params)
            self._load_namespaces(result)
        elif all(attrs):  # Everything is already specified and we're not told
            return        # to force a reload, so do nothing
        else:  # We're only loading attributes other than _namespaces
            params["siprop"] = "general"
            result = self._api_query(params)

        res = result["query"]["general"]
        self._name = res["wikiid"]
        self._project = res["sitename"].lower()
        self._lang = res["lang"]
        self._base_url = res["server"]
        self._article_path = res["articlepath"]
        self._script_path = res["scriptpath"]

    def _load_namespaces(self, result):
        """Fill self._namespaces with a dict of namespace IDs and names.

        Called by _load_attributes() with API data as `result` when
        self._namespaces was not given as an kwarg to __init__().
        """
        self._namespaces = {}

        for namespace in result["query"]["namespaces"].values():
            ns_id = namespace["id"]
            name = namespace["*"]
            try:
                canonical = namespace["canonical"]
            except KeyError:
                self._namespaces[ns_id] = [name]
            else:
                if name != canonical:
                    self._namespaces[ns_id] = [name, canonical]
                else:
                    self._namespaces[ns_id] = [name]

        for namespace in result["query"]["namespacealiases"]:
            ns_id = namespace["id"]
            alias = namespace["*"]
            self._namespaces[ns_id].append(alias)

    def _get_cookie(self, name, domain):
        """Return the named cookie unless it is expired or doesn't exist."""
        for cookie in self._cookiejar:
            if cookie.name == name and cookie.domain == domain:
                if cookie.is_expired():
                    break
                return cookie

    def _get_username_from_cookies(self):
        """Try to return our username based solely on cookies.

        First, we'll look for a cookie named self._name + "Token", like
        "enwikiToken". If it exists and isn't expired, we'll assume it's valid
        and try to return the value of the cookie self._name + "UserName" (like
        "enwikiUserName"). This should work fine on wikis without single-user
        login.

        If `enwikiToken` doesn't exist, we'll try to find a cookie named
        `centralauth_Token`. If this exists and is not expired, we'll try to
        return the value of `centralauth_User`.

        If we didn't get any matches, we'll return None. Our goal here isn't to
        return the most likely username, or what we *want* our username to be
        (for that, we'd do self._login_info[0]), but rather to get our current
        username without an unnecessary ?action=query&meta=userinfo API query. 
        """
        domain = self.domain()
        name = ''.join((self._name, "Token"))
        cookie = self._get_cookie(name, domain)

        if cookie is not None:
            name = ''.join((self._name, "UserName"))
            user_name = self._get_cookie(name, domain)
            if user_name is not None:
                return user_name.value

        name = "centralauth_Token"
        for cookie in self._cookiejar:            
            if cookie.domain_initial_dot is False or cookie.is_expired():
                continue
            if cookie.name != name:
                continue
            # Build a regex that will match domains this cookie affects:
            search = ''.join(("(.*?)", re_escape(cookie.domain)))
            if re_match(search, domain):  # Test it against our site
                user_name = self._get_cookie("centralauth_User", cookie.domain)
                if user_name is not None:
                    return user_name.value

    def _get_username_from_api(self):
        """Do a simple API query to get our username and return it.
        
        This is a reliable way to make sure we are actually logged in, because
        it doesn't deal with annoying cookie logic, but it results in an API
        query that is unnecessary in some cases.
        
        Called by _get_username() (in turn called by get_user() with no
        username argument) when cookie lookup fails, probably indicating that
        we are logged out.
        """
        params = {"action": "query", "meta": "userinfo"}
        result = self._api_query(params)
        return result["query"]["userinfo"]["name"]

    def _get_username(self):
        """Return the name of the current user, whether logged in or not.

        First, we'll try to deduce it solely from cookies, to avoid an
        unnecessary API query. For the cookie-detection method, see
        _get_username_from_cookies()'s docs.

        If our username isn't in cookies, then we're probably not logged in, or
        something fishy is going on (like forced logout). In this case, do a
        single API query for our username (or IP address) and return that.
        """
        name = self._get_username_from_cookies()
        if name is not None:
            return name
        return self._get_username_from_api()

    def _save_cookiejar(self):
        """Try to save our cookiejar after doing a (normal) login or logout.

        Calls the standard .save() method with no filename. Don't fret if our
        cookiejar doesn't support saving (CookieJar raises AttributeError,
        FileCookieJar raises NotImplementedError) or no default filename was
        given (LWPCookieJar and MozillaCookieJar raise ValueError).
        """
        try:
            self._cookiejar.save()
        except (AttributeError, NotImplementedError, ValueError):
            pass

    def _login(self, login, token=None, attempt=0):
        """Safely login through the API.

        Normally, this is called by __init__() if a username and password have
        been provided and no valid login cookies were found. The only other
        time it needs to be called is when those cookies expire, which is done
        automatically by api_query() if a query fails.

        Recent versions of MediaWiki's API have fixed a CSRF vulnerability,
        requiring login to be done in two separate requests. If the response
        from from our initial request is "NeedToken", we'll do another one with
        the token. If login is successful, we'll try to save our cookiejar.

        Raises LoginError on login errors (duh), like bad passwords and
        nonexistent usernames.

        `login` is a (username, password) tuple. `token` is the token returned
        from our first request, and `attempt` is to prevent getting stuck in a
        loop if MediaWiki isn't acting right.
        """
        name, password = login
        params = {"action": "login", "lgname": name, "lgpassword": password}
        if token is not None:
            params["lgtoken"] = token
        result = self._api_query(params)
        res = result["login"]["result"]

        if res == "Success":
            self._save_cookiejar()
        elif res == "NeedToken" and attempt == 0:
            token = result["login"]["token"]
            return self._login(login, token, attempt=1)
        else:
            if res == "Illegal":
                e = "The provided username is illegal."
            elif res == "NotExists":
                e = "The provided username does not exist."
            elif res == "EmptyPass":
                e = "No password was given."
            elif res == "WrongPass" or res == "WrongPluginPass":
                e = "The given password is incorrect."
            else:
                e = "Couldn't login; server says '{0}'.".format(res)
            raise LoginError(e)

    def _logout(self):
        """Safely logout through the API.

        We'll do a simple API request (api.php?action=logout), clear our
        cookiejar (which probably contains now-invalidated cookies) and try to
        save it, if it supports that sort of thing.
        """
        params = {"action": "logout"}
        self._api_query(params)
        self._cookiejar.clear()
        self._save_cookiejar()

    def _sql_connect(self, **kwargs):
        """Attempt to establish a connection with this site's SQL database.

        oursql.connect() will be called with self._sql_data as its kwargs,
        which is usually config.wiki["sites"][self.name()]["sql"]. Any kwargs
        given to this function will be passed to connect() and will have
        precedence over the config file.

        Will raise SQLError() if the module "oursql" is not available. oursql
        may raise its own exceptions (e.g. oursql.InterfaceError) if it cannot
        establish a connection.
        """
        if not oursql:
            e = "Module 'oursql' is required for SQL queries."
            raise SQLError(e)

        args = self._sql_data
        for key, value in kwargs.iteritems():
            args[key] = value

        if "read_default_file" not in args and "user" not in args and "passwd" not in args:
            args["read_default_file"] = expanduser("~/.my.cnf")

        self._sql_conn = oursql.connect(**args)

    def name(self):
        """Returns the Site's name (or "wikiid" in the API), like "enwiki"."""
        return self._name

    def project(self):
        """Returns the Site's project name in lowercase, like "wikipedia"."""
        return self._project

    def lang(self):
        """Returns the Site's language code, like "en" or "es"."""
        return self._lang

    def domain(self):
        """Returns the Site's web domain, like "en.wikipedia.org"."""
        return urlparse(self._base_url).netloc

    def api_query(self, **kwargs):
        """Do an API query with `kwargs` as the parameters.

        See _api_query()'s documentation for details.
        """
        return self._api_query(kwargs)

    def sql_query(self, query, params=(), plain_query=False, dict_cursor=False,
                  cursor_class=None, show_table=False):
        """Do an SQL query and yield its results.

        If `plain_query` is True, we will force an unparameterized query.
        Specifying both params and plain_query will cause an error.

        If `dict_cursor` is True, we will use oursql.DictCursor as our cursor,
        otherwise the default oursql.Cursor. If `cursor_class` is given, it
        will override this option.

        If `show_table` is True, the name of the table will be prepended to the
        name of the column. This will mainly affect a DictCursor.

        Example:
        >>> query = "SELECT user_id, user_registration FROM user WHERE user_name = ?"
        >>> params = ("The Earwig",)
        >>> result1 = site.sql_query(query, params)
        >>> result2 = site.sql_query(query, params, dict_cursor=True)
        >>> for row in result1: print row
        (7418060L, '20080703215134')
        >>> for row in result2: print row
        {'user_id': 7418060L, 'user_registration': '20080703215134'}

        See _sql_connect() for information on how a connection is acquired.

        <http://packages.python.org/oursql> has helpful documentation on the
        oursql module.

        This may raise SQLError() or one of oursql's exceptions
        (oursql.ProgrammingError, oursql.InterfaceError, ...) if there were
        problems with the query.
        """
        if not self._sql_conn:
            self._sql_connect()

        if not cursor_class:
            if dict_cursor:
                cursor_class = oursql.DictCursor
            else:
                cursor_class = oursql.Cursor

        with self._sql_conn.cursor(cursor_class, show_table=show_table) as cur:
            cur.execute(query, params, plain_query)
            for result in cur:
                yield result

    def get_replag(self):
        """Return the estimated database replication lag in seconds.
        
        Requires SQL access. This function only makes sense on a replicated
        database (e.g. the Wikimedia Toolserver) and on a wiki that receives a
        large number of edits (ideally, at least one per second), or the result
        may be larger than expected. 
        """
        query = "SELECT NOW() - MAX(rev_timestamp) FROM revision"
        result = list(self.sql_query(query))
        return result[0][0]

    def namespace_id_to_name(self, ns_id, all=False):
        """Given a namespace ID, returns associated namespace names.

        If all is False (default), we'll return the first name in the list,
        which is usually the localized version. Otherwise, we'll return the
        entire list, which includes the canonical name.

        For example, returns u"Wikipedia" if ns_id=4 and all=False on enwiki;
        returns [u"Wikipedia", u"Project"] if ns_id=4 and all=True.

        Raises NamespaceNotFoundError if the ID is not found.
        """
        try:
            if all:
                return self._namespaces[ns_id]
            else:
                return self._namespaces[ns_id][0]
        except KeyError:
            e = "There is no namespace with id {0}.".format(ns_id)
            raise NamespaceNotFoundError(e)

    def namespace_name_to_id(self, name):
        """Given a namespace name, returns the associated ID.

        Like namespace_id_to_name(), but reversed. Case is ignored, because
        namespaces are assumed to be case-insensitive.

        Raises NamespaceNotFoundError if the name is not found.
        """
        lname = name.lower()
        for ns_id, names in self._namespaces.items():
            lnames = [n.lower() for n in names]  # Be case-insensitive
            if lname in lnames:
                return ns_id

        e = "There is no namespace with name '{0}'.".format(name)
        raise NamespaceNotFoundError(e)

    def get_page(self, title, follow_redirects=False):
        """Returns a Page object for the given title (pagename).

        Will return a Category object instead if the given title is in the
        category namespace. As Category is a subclass of Page, this should not
        cause problems.

        Note that this doesn't do any direct checks for existence or
        redirect-following - Page's methods provide that.
        """
        prefixes = self.namespace_id_to_name(NS_CATEGORY, all=True)
        prefix = title.split(":", 1)[0]
        if prefix != title:  # Avoid a page that is simply "Category"
            if prefix in prefixes:
                return Category(self, title, follow_redirects)
        return Page(self, title, follow_redirects)

    def get_category(self, catname, follow_redirects=False):
        """Returns a Category object for the given category name.

        `catname` should be given *without* a namespace prefix. This method is
        really just shorthand for get_page("Category:" + catname).
        """
        prefix = self.namespace_id_to_name(NS_CATEGORY)
        pagename = ':'.join((prefix, catname))
        return Category(self, pagename, follow_redirects)

    def get_user(self, username=None):
        """Returns a User object for the given username.

        If `username` is left as None, then a User object representing the
        currently logged-in (or anonymous!) user is returned.
        """
        if username is None:
            username = self._get_username()
        return User(self, username)
