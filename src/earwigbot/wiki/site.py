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

__all__ = ["Site"]

import json
import os.path
import time
import typing
from collections.abc import Callable, Generator, Sequence
from http.cookiejar import Cookie, CookieJar
from logging import Logger, NullHandler, getLogger
from threading import RLock
from typing import Any, Literal, ParamSpec, TypedDict, TypeVar
from urllib.parse import unquote_plus, urlparse

import requests
from requests.cookies import RequestsCookieJar
from requests_oauthlib import OAuth1

from earwigbot import exceptions
from earwigbot.wiki import constants
from earwigbot.wiki.category import Category
from earwigbot.wiki.constants import Service
from earwigbot.wiki.page import Page
from earwigbot.wiki.user import User

if typing.TYPE_CHECKING:
    import pymysql
    import pymysql.cursors
    from pymysql.cursors import Cursor
else:
    try:
        import pymysql
        import pymysql.cursors
    except ModuleNotFoundError:
        pymysql = None

T = TypeVar("T")
P = ParamSpec("P")

ApiParams = dict[str, str | int]
ApiResult = dict[str, Any]
SqlConnInfo = dict[str, Any]


class OAuthInfo(TypedDict):
    consumer_token: str
    consumer_secret: str
    access_token: str
    access_secret: str


class _ApiInfoCache(TypedDict):
    maxlag: int
    lastcheck: float


class _SqlInfoCache(TypedDict):
    replag: int
    lastcheck: float
    usable: bool | None


class Site:
    """
    **EarwigBot: Wiki Toolset: Site**

    Represents a site, with support for API queries and returning
    :py:class:`~earwigbot.wiki.page.Page`, :py:class:`~earwigbot.wiki.user.User`, and
    :py:class:`~earwigbot.wiki.category.Category` objects. The constructor takes a
    bunch of arguments and you probably won't need to call it directly, rather
    :py:meth:`wiki.get_site() <earwigbot.wiki.sitesdb.SitesDB.get_site>` for returning
    :py:class:`Site` instances, :py:meth:`wiki.add_site()
    <earwigbot.wiki.sitesdb.SitesDB.add_site>` for adding new ones to our database, and
    :py:meth:`wiki.remove_site() <earwigbot.wiki.sitesdb.SitesDB.remove_site>` for
    removing old ones from our database, should suffice.

    *Attributes:*

    - :py:attr:`name`:    the site's name (or "wikiid"), like ``"enwiki"``
    - :py:attr:`project`: the site's project name, like ``"wikipedia"``
    - :py:attr:`lang`:    the site's language code, like ``"en"``
    - :py:attr:`domain`:  the site's web domain, like ``"en.wikipedia.org"``
    - :py:attr:`url`:     the site's URL, like ``"https://en.wikipedia.org"``

    *Public methods:*

    - :py:meth:`api_query`:            does an API query with kwargs as params
    - :py:meth:`sql_query`:            does an SQL query and yields its results
    - :py:meth:`get_maxlag`:           returns the internal database lag
    - :py:meth:`get_replag`:           estimates the external database lag
    - :py:meth:`get_token`:            gets a token for a specific API action
    - :py:meth:`namespace_id_to_name`: returns names associated with an NS id
    - :py:meth:`namespace_name_to_id`: returns the ID associated with a NS name
    - :py:meth:`get_page`:             returns a Page for the given title
    - :py:meth:`get_category`:         returns a Category for the given title
    - :py:meth:`get_user`:             returns a User object for the given name
    - :py:meth:`delegate`:             controls when the API or SQL is used
    """

    SPECIAL_TOKENS = [
        "createaccount",
        "deleteglobalaccount",
        "login",
        "patrol",
        "rollback",
        "setglobalaccountstatus",
        "userrights",
        "watch",
    ]

    def __init__(
        self,
        name: str | None = None,
        project: str | None = None,
        lang: str | None = None,
        base_url: str | None = None,
        article_path: str | None = None,
        script_path: str | None = None,
        sql: SqlConnInfo | None = None,
        namespaces: dict[int, list[str]] | None = None,
        login: tuple[str, str] | tuple[None, None] = (None, None),
        oauth: OAuthInfo | None = None,
        cookiejar: CookieJar | None = None,
        user_agent: str | None = None,
        use_https: bool = True,
        assert_edit: bool | None = None,
        maxlag: int | None = None,
        wait_between_queries: int = 1,
        logger: Logger | None = None,
        search_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Constructor for new Site instances.

        This probably isn't necessary to call yourself unless you're building a Site
        that's not in your config and you don't want to add it - normally all you need
        is wiki.get_site(name), which creates the Site for you based on your config file
        and the sites database. We accept a bunch of kwargs, but the only ones you
        really "need" are *base_url* and *script_path*; this is enough to figure out an
        API url. *login*, a tuple of (username, password), can be used to log in using
        the legacy BotPasswords system; otherwise, a dict of OAuth info should be
        provided to *oauth*. *cookiejar* will be used to store cookies, and we'll use a
        normal CookieJar if none is given.

        First, we'll store the given arguments as attributes, then set up our requests
        session. We'll load any of the attributes that weren't given from the API, and
        then log in if a username/pass was given and we aren't already logged in.
        """
        # Attributes referring to site information, filled in by an API query # if they
        # are missing (and an API url can be determined):
        self._name = name
        self._project = project
        self._lang = lang
        self._base_url = base_url
        self._article_path = article_path
        self._script_path = script_path
        self._namespaces: dict[int, list[str]] | None = namespaces

        # Attributes used for API queries:
        self._use_https = use_https
        self._assert_edit = assert_edit
        self._maxlag = maxlag
        self._wait_between_queries = wait_between_queries
        self._max_retries = 6
        self._last_query_time = 0
        self._tokens: dict[str, str] = {}
        self._api_lock = RLock()
        self._api_info_cache = _ApiInfoCache(maxlag=0, lastcheck=0)

        # Attributes used for SQL queries:
        if sql:
            self._sql_data = sql
        else:
            self._sql_data: SqlConnInfo = {}
        self._sql_conn = None
        self._sql_lock = RLock()
        self._sql_info_cache = _SqlInfoCache(replag=0, lastcheck=0, usable=None)

        # Attribute used in copyright violation checks (see CopyrightMixIn):
        if search_config:
            self._search_config = search_config
        else:
            self._search_config = {}

        # Set up cookiejar and requests session for making API queries:
        if cookiejar is not None:
            self._cookiejar = cookiejar
        else:
            self._cookiejar = CookieJar()
        self._last_cookiejar_save = None
        if not user_agent:
            user_agent = constants.USER_AGENT  # Set default UA
        self._oauth = oauth
        self._session = requests.Session()
        self._session.cookies = typing.cast(RequestsCookieJar, self._cookiejar)
        self._session.headers["User-Agent"] = user_agent
        if oauth:
            self._session.auth = OAuth1(
                oauth["consumer_token"],
                oauth["consumer_secret"],
                oauth["access_token"],
                oauth["access_secret"],
            )

        # Set up our internal logger:
        if logger:
            self._logger = logger
        else:  # Just set up a null logger to eat up our messages:
            self._logger = getLogger("earwigbot.wiki")
            self._logger.addHandler(NullHandler())

        # Get all of the above attributes that were not specified as arguments:
        self._load_attributes()

        # If we have a name/pass and the API says we're not logged in, log in:
        self._login_user, self._login_password = login
        if not self._oauth and self._login_user and self._login_password:
            logged_in_as = self._get_username_from_cookies()
            if not logged_in_as or self._login_user.replace("_", " ") != logged_in_as:
                self._login()

    def __repr__(self) -> str:
        """
        Return the canonical string representation of the Site.
        """
        res = ", ".join(
            (
                "Site(name={_name!r}",
                "project={_project!r}",
                "lang={_lang!r}",
                "base_url={_base_url!r}",
                "article_path={_article_path!r}",
                "script_path={_script_path!r}",
                "use_https={_use_https!r}",
                "assert_edit={_assert_edit!r}",
                "maxlag={_maxlag!r}",
                "sql={_sql_data!r}",
                "login={0}",
                "oauth={1}",
                "user_agent={3!r}",
                "cookiejar={2})",
            )
        )
        login = f"({self._login_user!r}, {'hidden' if self._login_password else None})"
        oauth = "hidden" if self._oauth else None
        cookies = self._cookiejar.__class__.__name__
        if hasattr(self._cookiejar, "filename"):
            cookies += "({!r})".format(getattr(self._cookiejar, "filename"))
        else:
            cookies += "()"
        agent = self.user_agent
        return res.format(login, oauth, cookies, agent, **self.__dict__)

    def __str__(self) -> str:
        """
        Return a nice string representation of the Site.
        """
        res = "<Site {0} ({1}:{2}) at {3}>"
        return res.format(self.name, self.project, self.lang, self.domain)

    def _api_query(
        self,
        params: ApiParams,
        tries: int = 0,
        wait: int = 5,
        ignore_maxlag: bool = False,
        no_assert: bool = False,
        ae_retry: bool = True,
    ) -> ApiResult:
        """
        Do an API query with *params* as a dict of parameters.

        See the documentation for :py:meth:`api_query` for full implementation details.
        *tries*, *wait*, and *ignore_maxlag* are for maxlag; *no_assert* and *ae_retry*
        are for AssertEdit.
        """
        since_last_query = time.time() - self._last_query_time  # Throttling support
        if since_last_query < self._wait_between_queries:
            wait_time = self._wait_between_queries - since_last_query
            log = f"Throttled: waiting {round(wait_time, 2)} seconds"
            self._logger.debug(log)
            time.sleep(wait_time)
        self._last_query_time = time.time()

        url, params = self._build_api_query(params, ignore_maxlag, no_assert)
        if "lgpassword" in params:
            self._logger.debug(f"{url} -> <hidden>")
        else:
            data = json.dumps(params)
            if len(data) > 1000:
                self._logger.debug(f"{url} -> {data[:997]}...")
            else:
                self._logger.debug(f"{url} -> {data}")

        try:
            response = self._session.post(url, data=params)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise exceptions.APIError(f"API query failed: {exc}")

        return self._handle_api_result(response, params, tries, wait, ae_retry)

    def _request_csrf_token(self, params: ApiParams) -> None:
        """
        If possible, add a request for a CSRF token to an API query.
        """
        if params.get("action") == "query":
            if params.get("meta"):
                assert isinstance(params["meta"], str), params["meta"]
                if "tokens" not in params["meta"].split("|"):
                    params["meta"] += "|tokens"
            else:
                params["meta"] = "tokens"
            if params.get("type"):
                assert isinstance(params["type"], str), params["type"]
                if "csrf" not in params["type"].split("|"):
                    params["type"] += "|csrf"

    def _build_api_query(
        self, params: ApiParams, ignore_maxlag: bool, no_assert: bool
    ) -> tuple[str, ApiParams]:
        """
        Given API query params, return the URL to query and POST data.
        """
        if not self._base_url or self._script_path is None:
            e = "Tried to do an API query, but no API URL is known."
            raise exceptions.APIError(e)

        url = self.url + self._script_path + "/api.php"
        params["format"] = "json"  # This is the only format we understand
        if self._assert_edit and not no_assert:
            # If requested, ensure that we're logged in
            params["assert"] = self._assert_edit
        if self._maxlag and not ignore_maxlag:
            # If requested, don't overload the servers:
            params["maxlag"] = self._maxlag
        if "csrf" not in self._tokens:
            # If we don't have a CSRF token, try to fetch one:
            self._request_csrf_token(params)
        return url, params

    def _handle_api_result(
        self,
        response: requests.Response,
        params: ApiParams,
        tries: int,
        wait: int,
        ae_retry: bool,
    ) -> ApiResult:
        """
        Given an API query response, attempt to return useful data.
        """
        try:
            res = response.json()
        except ValueError:
            e = "API query failed: JSON could not be decoded."
            raise exceptions.APIError(e)

        if "warnings" in res:
            for name, value in res["warnings"].items():
                try:
                    warning = value["warnings"]
                except KeyError:
                    try:
                        warning = value["*"]
                    except KeyError:
                        warning = value
                self._logger.warning("API warning: %s: %s", name, warning)

        if self._should_save_cookiejar():
            self._save_cookiejar()

        try:
            code = res["error"]["code"]
            info = res["error"]["info"]
        except (TypeError, KeyError):  # If there's no error code/info, return
            if "query" in res and "tokens" in res["query"]:
                for name, token in res["query"]["tokens"].items():
                    self._tokens[name.split("token")[0]] = token
            return res

        if code == "maxlag":  # We've been throttled by the server
            if tries >= self._max_retries:
                e = "Maximum number of retries reached ({0})."
                raise exceptions.APIError(e.format(self._max_retries))
            tries += 1
            msg = 'Server says "{0}"; retrying in {1} seconds ({2}/{3})'
            self._logger.info(msg.format(info, wait, tries, self._max_retries))
            time.sleep(wait)
            return self._api_query(params, tries, wait * 2, ae_retry=ae_retry)
        elif code in ["assertuserfailed", "assertbotfailed"]:  # AssertEdit
            if (
                ae_retry
                and self._login_user
                and self._login_password
                and not self._oauth
            ):
                # Try to log in if we got logged out:
                self._login()
                if "token" in params:  # Fetch a new one; this is invalid now
                    assert isinstance(params["action"], str), params["action"]
                    params["token"] = self.get_token(params["action"])
                return self._api_query(params, tries, wait, ae_retry=False)
            if not self._oauth and not (self._login_user and self._login_password):
                e = "Assertion failed, and no login info was provided."
            elif code == "assertbotfailed":
                e = "Bot assertion failed: we don't have a bot flag!"
            else:
                e = "User assertion failed due to an unknown issue. Cookie or OAuth problem?"
            raise exceptions.PermissionsError("AssertEdit: " + e)
        else:  # Some unknown error occurred
            e = 'API query failed: got error "{0}"; server says: "{1}".'
            error = exceptions.APIError(e.format(code, info))
            error.code, error.info = code, info
            raise error

    def _load_attributes(self, force: bool = False) -> None:
        """
        Load data about our Site from the API.

        This function is called by __init__() when one of the site attributes was not
        given as a keyword argument. We'll do an API query to get the missing data, but
        only if there actually *is* missing data.

        Additionally, you can call this with *force* set to True to forcibly reload
        all attributes.
        """
        # All attributes to be loaded, except _namespaces, which is a special
        # case because it requires additional params in the API query:
        attrs = [
            self._name,
            self._project,
            self._lang,
            self._base_url,
            self._article_path,
            self._script_path,
        ]

        params: ApiParams = {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "general",
        }

        if not self._namespaces or force:
            assert isinstance(params["siprop"], str), params["siprop"]
            params["siprop"] += "|namespaces|namespacealiases"
            with self._api_lock:
                result = self._api_query(params, no_assert=True)
            self._load_namespaces(result)
        elif all(attrs):
            # Everything is already specified and we're not told to force a reload,
            # so do nothing
            return
        else:
            # We're only loading attributes other than _namespaces
            with self._api_lock:
                result = self._api_query(params, no_assert=True)

        res = result["query"]["general"]
        self._name = res["wikiid"]
        self._project = res["sitename"].lower()
        self._lang = res["lang"]
        self._base_url = res["server"]
        self._article_path = res["articlepath"]
        self._script_path = res["scriptpath"]

    def _load_namespaces(self, result: ApiResult) -> None:
        """
        Fill self._namespaces with a dict of namespace IDs and names.

        Called by _load_attributes() with API data as *result* when self._namespaces
        was not given as an kwarg to __init__().
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

    def _get_cookie(self, name: str, domain: str) -> Cookie | None:
        """
        Return the named cookie unless it is expired or doesn't exist.
        """
        for cookie in self._cookiejar:
            if cookie.name == name and cookie.domain == domain:
                if cookie.is_expired():
                    break
                return cookie

    def _get_username_from_cookies(self) -> str | None:
        """
        Try to return our username based solely on cookies.

        First, we'll look for a cookie named self._name + "Token", like "enwikiToken".
        If it exists and isn't expired, we'll assume it's valid and try to return the
        value of the cookie self._name + "UserName" (like "enwikiUserName"). This
        should work fine on wikis without single-user login.

        If `enwikiToken` doesn't exist, we'll try to find a cookie named
        `centralauth_Token`. If this exists and is not expired, we'll try to return the
        value of `centralauth_User`.

        If we didn't get any matches, we'll return None. Our goal here isn't to return
        the most likely username, or what we *want* our username to be (for that, we'd
        do self._login_user), but rather to get our current username without an
        unnecessary ?action=query&meta=userinfo API query.
        """
        name = f"{self.name}Token"
        cookie = self._get_cookie(name, self.domain)

        if cookie:
            name = f"{self.name}UserName"
            user_name = self._get_cookie(name, self.domain)
            if user_name:
                assert user_name.value, user_name
                return unquote_plus(user_name.value)

        for cookie in self._cookiejar:
            if cookie.name != "centralauth_Token" or cookie.is_expired():
                continue
            base = cookie.domain
            if base.startswith(".") and not cookie.domain_initial_dot:
                base = base[1:]
            if self.domain.endswith(base):
                user_name = self._get_cookie("centralauth_User", cookie.domain)
                if user_name:
                    assert user_name.value, user_name
                    return unquote_plus(user_name.value)

    def _get_username_from_api(self) -> str:
        """
        Do a simple API query to get our username and return it.

        This is a reliable way to make sure we are actually logged in, because it
        doesn't deal with annoying cookie logic, but it results in an API query that is
        unnecessary in some cases.

        Called by _get_username() (in turn called by get_user() with no username
        argument) when cookie lookup fails, probably indicating that we are logged out.
        """
        result = self.api_query(action="query", meta="userinfo")
        return result["query"]["userinfo"]["name"]

    def _get_username(self) -> str:
        """
        Return the name of the current user, whether logged in or not.

        First, we'll try to deduce it solely from cookies, to avoid an unnecessary API
        query. For the cookie-detection method, see _get_username_from_cookies()'s docs.

        If our username isn't in cookies, then we're either using OAuth or we're
        probably not logged in, or something fishy is going on (like forced logout).
        If we're using OAuth and a username was configured, assume it is accurate and
        use it. Otherwise, do a single API query for our username (or IP address) and
        return that.
        """
        name = self._get_username_from_cookies()
        if name:
            return name
        if self._oauth and self._login_user:
            return self._login_user
        return self._get_username_from_api()

    def _should_save_cookiejar(self) -> bool:
        """
        Return a bool indicating whether we should save the cookiejar.

        This is True if we haven't saved the cookiejar yet this session, or if our last
        save was over a day ago.
        """
        max_staleness = 60 * 60 * 24  # 1 day
        if not self._last_cookiejar_save:
            return True
        return time.time() - self._last_cookiejar_save > max_staleness

    def _save_cookiejar(self) -> None:
        """
        Try to save our cookiejar after doing a (normal) login or logout.

        Calls the standard .save() method with no filename. Don't fret if our cookiejar
        doesn't support saving (CookieJar raises AttributeError, FileCookieJar raises
        NotImplementedError) or no default filename was given (LWPCookieJar and
        MozillaCookieJar raise ValueError).
        """
        if hasattr(self._cookiejar, "save"):
            try:
                getattr(self._cookiejar, "save")()
            except (NotImplementedError, ValueError):
                pass
        self._last_cookiejar_save = time.time()

    def _login(self) -> None:
        """
        Safely login through the API.

        Normally, this is called by __init__() if a username and password have been
        provided and no valid login cookies were found. The only other time it needs to
        be called is when those cookies expire, which is done automatically by
        api_query() if a query fails.

        Raises LoginError on login errors (duh), like bad passwords and
        nonexistent usernames.
        """
        assert self._login_user
        assert self._login_password
        self._tokens.clear()

        params: ApiParams = {"action": "query", "meta": "tokens", "type": "login"}
        with self._api_lock:
            result = self._api_query(params, no_assert=True)
        try:
            token = result["query"]["tokens"]["logintoken"]
        except KeyError:
            raise exceptions.LoginError("Couldn't get login token")

        params = {
            "action": "login",
            "lgname": self._login_user,
            "lgpassword": self._login_password,
            "lgtoken": token,
        }
        with self._api_lock:
            result = self._api_query(params, no_assert=True)

        res = result["login"]["result"]
        if res == "Success":
            self._tokens.clear()
            self._save_cookiejar()
            return
        if res == "Illegal":
            e = "The provided username is illegal."
        elif res == "NotExists":
            e = "The provided username does not exist."
        elif res == "EmptyPass":
            e = "No password was given."
        elif res == "WrongPass" or res == "WrongPluginPass":
            e = "The given password is incorrect."
        else:
            e = f"Couldn't login; server says '{res}'."
        raise exceptions.LoginError(e)

    def _logout(self) -> None:
        """
        Safely logout through the API.

        We'll do a simple API request (api.php?action=logout), clear our cookiejar
        (which probably contains now-invalidated cookies) and try to save it, if it
        supports that sort of thing.
        """
        self.api_query(action="logout")
        self._cookiejar.clear()
        self._save_cookiejar()

    def _sql_connect(self, **kwargs: Any) -> pymysql.Connection[Cursor]:
        """
        Attempt to establish a connection with this site's SQL database.

        pymysql.connect() will be called with self._sql_data as its kwargs. Any kwargs
        given to this function will be passed to connect() and will have precedence
        over the config file.

        Will raise SQLError() if the module "pymysql" is not available. pymysql may
        raise its own exceptions (e.g. pymysql.InterfaceError) if it cannot establish
        a connection.
        """
        args = self._sql_data
        for key, value in kwargs.items():
            args[key] = value
        if (
            "read_default_file" not in args
            and "user" not in args
            and "passwd" not in args
        ):
            args["read_default_file"] = os.path.expanduser("~/.my.cnf")
        elif "read_default_file" in args:
            args["read_default_file"] = os.path.expanduser(args["read_default_file"])
        if "autoping" not in args:
            args["autoping"] = True
        if "autoreconnect" not in args:
            args["autoreconnect"] = True

        if pymysql is None:
            raise exceptions.SQLError(
                "SQL querying requires the 'pymysql' package: https://pymysql.readthedocs.io/"
            )
        return pymysql.connect(**args)

    def _get_service_order(self) -> list[Service]:
        """
        Return a preferred order for using services (e.g. the API and SQL).

        A list is returned, starting with the most preferred service first and ending
        with the least preferred one. Currently, there are only two services.
        SERVICE_API will always be included since the API is expected to be always
        usable. In normal circumstances, self.SERVICE_SQL will be first (with the API
        second), since using SQL directly is easier on the servers than making web
        queries with the API. self.SERVICE_SQL will be second if replag is greater than
        three minutes (a cached value updated every two minutes at most), *unless* API
        lag is also very high. self.SERVICE_SQL will not be included in the list if we
        cannot form a proper SQL connection.
        """
        if pymysql is None:
            self._sql_info_cache["usable"] = False
            return [Service.API]

        now = time.time()
        if now - self._sql_info_cache["lastcheck"] > 120:
            self._sql_info_cache["lastcheck"] = now
            try:
                try:
                    self._sql_info_cache["replag"] = sqllag = self.get_replag()
                except pymysql.Error as exc:
                    raise exceptions.SQLError(str(exc))
            except exceptions.SQLError:
                self._sql_info_cache["usable"] = False
                return [Service.API]
            self._sql_info_cache["usable"] = True
        else:
            if not self._sql_info_cache["usable"]:
                return [Service.API]
            sqllag = self._sql_info_cache["replag"]

        if sqllag > 300:
            if not self._maxlag:
                return [Service.API, Service.SQL]
            if now - self._api_info_cache["lastcheck"] > 300:
                self._api_info_cache["lastcheck"] = now
                try:
                    self._api_info_cache["maxlag"] = apilag = self.get_maxlag()
                except exceptions.APIError:
                    self._api_info_cache["maxlag"] = apilag = 0
            else:
                apilag = self._api_info_cache["maxlag"]
            if apilag > self._maxlag:
                return [Service.SQL, Service.API]
            return [Service.API, Service.SQL]

        return [Service.SQL, Service.API]

    @property
    def name(self) -> str:
        """
        The Site's name (or "wikiid" in the API), like ``"enwiki"``.
        """
        assert self._name is not None
        return self._name

    @property
    def project(self) -> str:
        """
        The Site's project name in lowercase, like ``"wikipedia"``.
        """
        assert self._project is not None
        return self._project

    @property
    def lang(self) -> str:
        """
        The Site's language code, like ``"en"`` or ``"es"``.
        """
        assert self._lang is not None
        return self._lang

    @property
    def base_url(self) -> str:
        """
        The Site's base URL, like ``"https://en.wikipedia.org"``.

        May be protocol-relative (e.g. ``"//en.wikipedia.org"``). See :py:attr:`url`
        for an alternative.
        """
        assert self._base_url is not None
        return self._base_url

    @property
    def domain(self) -> str:
        """
        The Site's web domain, like ``"en.wikipedia.org"``.
        """
        return urlparse(self.base_url).netloc

    @property
    def url(self) -> str:
        """
        The Site's full base URL, like ``"https://en.wikipedia.org"``.
        """
        url = self.base_url
        if url.startswith("//"):  # Protocol-relative URLs from 1.18
            if self._use_https:
                url = "https:" + url
            else:
                url = "http:" + url
        return url

    @property
    def article_path(self) -> str:
        """
        The base URL used to construct internal links, like ``"/wiki/$1"``.
        """
        assert self._article_path is not None
        return self._article_path

    @property
    def script_path(self) -> str:
        """
        The base URL used to refer to other parts of the wiki, like ``"/w"``.
        """
        assert self._script_path is not None
        return self._script_path

    @property
    def user_agent(self) -> str:
        """
        The User-Agent header sent to the API by the requests session.
        """
        user_agent = self._session.headers["User-Agent"]
        assert isinstance(user_agent, str), user_agent
        return user_agent

    @property
    def namespaces(self) -> dict[int, list[str]]:
        """
        The mapping of namespace IDs to namespace names.
        """
        assert self._namespaces
        return self._namespaces

    def api_query(self, **kwargs: str | int) -> ApiResult:
        """
        Do an API query with `kwargs` as the parameters.

        This will first attempt to construct an API url from :py:attr:`self._base_url`
        and :py:attr:`self._script_path`. We need both of these, or else we'll raise
        :py:exc:`~earwigbot.exceptions.APIError`. If :py:attr:`self._base_url` is
        protocol-relative (introduced in MediaWiki 1.18), we'll choose HTTPS only if
        :py:attr:`self._user_https` is ``True``, otherwise HTTP.

        We'll encode the given params, adding ``format=json`` along the way, as well as
        ``&assert=`` and ``&maxlag=`` based on :py:attr:`self._assert_edit` and
        :py:attr:`_maxlag` respectively. Additionally, we'll sleep a bit if the last
        query was made fewer than :py:attr:`self._wait_between_queries` seconds ago.
        The request is made through :py:attr:`self._session`, which has cookie support
        (:py:attr:`self._cookiejar`) and a ``User-Agent``
        (:py:const:`earwigbot.wiki.constants.USER_AGENT`).

        Assuming everything went well, we'll gunzip the data (if compressed), load it
        as a JSON object, and return it.

        If our request failed for some reason, we'll raise
        :py:exc:`~earwigbot.exceptions.APIError` with details. If that reason was due
        to maxlag, we'll sleep for a bit and then repeat the query until we exceed
        :py:attr:`self._max_retries`.

        There is helpful MediaWiki API documentation at `MediaWiki.org
        <https://www.mediawiki.org/wiki/API>`_.
        """
        with self._api_lock:
            return self._api_query(kwargs)

    @typing.overload
    def sql_query(
        self,
        query: str,
        params: Sequence[Any] = (),
        *,
        dict_cursor: Literal[False] = False,
        cursor_class: None = None,
        buffsize: int = 1024,
    ) -> Generator[tuple[Any, ...], None, None]: ...

    @typing.overload
    def sql_query(
        self,
        query: str,
        params: Sequence[Any] = (),
        *,
        dict_cursor: Literal[True],
        cursor_class: None = None,
        buffsize: int = 1024,
    ) -> Generator[dict[str, Any], None, None]: ...

    @typing.overload
    def sql_query(
        self,
        query: str,
        params: Sequence[Any] = (),
        *,
        dict_cursor: bool = False,
        cursor_class: type[pymysql.cursors.DictCursor],
        buffsize: int = 1024,
    ) -> Generator[dict[str, Any], None, None]: ...

    def sql_query(
        self,
        query: str,
        params: Sequence[Any] = (),
        *,
        dict_cursor: bool = False,
        cursor_class: type[Cursor] | None = None,
        buffsize: int = 1024,
    ) -> Generator[tuple[Any, ...] | dict[str, Any], None, None]:
        """
        Do an SQL query and yield its results.

        If *plain_query* is ``True``, we will force an unparameterized query.
        Specifying both *params* and *plain_query* will cause an error. If
        *dict_cursor* is ``True``, we will use :py:class:`pymysql.cursors.DictCursor`
        as our cursor, otherwise the default :py:class:`pymysql.cursors.Cursor`. If
        *cursor_class* is given, it will override this option.

        *buffsize* is the size of each memory-buffered group of results, to reduce the
        number of conversations with the database; it is passed to
        :py:meth:`cursor.fetchmany() <pymysql.cursors.Cursor.fetchmany>`. If set to
        ``0```, all results will be buffered in memory at once (this uses
        :py:meth:`fetchall() <pymysql.cursors.Cursor.fetchall>`). If set to ``1``, it
        is equivalent to using :py:meth:`fetchone() <pymysql.cursors.Cursor.fetchone>`.

        Example usage::

            >>> query = "SELECT user_id, user_registration FROM user WHERE user_name = ?"
            >>> params = ("The Earwig",)
            >>> result1 = site.sql_query(query, params)
            >>> result2 = site.sql_query(query, params, dict_cursor=True)
            >>> for row in result1: print row
            (7418060L, '20080703215134')
            >>> for row in result2: print row
            {'user_id': 7418060L, 'user_registration': '20080703215134'}

        This may raise :py:exc:`~earwigbot.exceptions.SQLError` or one of pymysql's
        exceptions (:py:exc:`pymysql.ProgrammingError`,
        :py:exc:`pymysql.InterfaceError`, ...) if there were problems with the query.

        See :py:meth:`_sql_connect` for information on how a connection is acquired.
        Also relevant is `pymysql's documentation <https://pymysql.readthedocs.io/>`_
        for details on that package.
        """
        if not cursor_class:
            if dict_cursor:
                cursor_class = pymysql.cursors.DictCursor
            else:
                cursor_class = pymysql.cursors.Cursor
        klass = cursor_class

        with self._sql_lock:
            if not self._sql_conn:
                self._sql_conn = self._sql_connect()

            with self._sql_conn.cursor(klass) as cur:
                cur.execute(query, params)
                if buffsize:
                    while group := cur.fetchmany(buffsize):
                        yield from group
                else:
                    yield from cur.fetchall()

    @typing.overload
    def get_maxlag(self, showall: Literal[False] = False) -> int: ...

    @typing.overload
    def get_maxlag(self, showall: Literal[True]) -> list[int]: ...

    def get_maxlag(self, showall: bool = False) -> int | list[int]:
        """
        Return the internal database replication lag in seconds.

        In a typical setup, this function returns the replication lag *within* the
        WMF's cluster, *not* external replication lag affecting Toolforge (see
        :py:meth:`get_replag` for that). This is useful when combined with the
        ``maxlag`` API query param (added by config), in which queries will be halted
        and retried if the lag is too high, usually above five seconds.

        With *showall*, will return a list of the lag for all servers in the cluster,
        not just the one with the highest lag.
        """
        params: ApiParams = {
            "action": "query",
            "meta": "siteinfo",
            "siprop": "dbrepllag",
        }
        if showall:
            params["sishowalldb"] = 1
        with self._api_lock:
            result = self._api_query(params, ignore_maxlag=True)
        if showall:
            return [server["lag"] for server in result["query"]["dbrepllag"]]
        return result["query"]["dbrepllag"][0]["lag"]

    def get_replag(self) -> int:
        """
        Return the estimated external database replication lag in seconds.

        Requires SQL access. This function only makes sense on a replicated database
        (e.g. Wikimedia Toolforge) and on a wiki that receives a large number of edits
        (ideally, at least one per second), or the result may be larger than expected,
        since it works by subtracting the current time from the timestamp of the latest
        recent changes event.

        This may raise :py:exc:`~earwigbot.exceptions.SQLError` or one of pymysql's
        exceptions (:py:exc:`pymysql.ProgrammingError`,
        :py:exc:`pymysql.InterfaceError`, ...) if there were problems.
        """
        query = """SELECT UNIX_TIMESTAMP() - UNIX_TIMESTAMP(rc_timestamp) FROM
                   recentchanges ORDER BY rc_timestamp DESC LIMIT 1"""
        result = list(self.sql_query(query))
        return int(result[0][0])

    def get_token(self, action: str | None = None, force: bool = False) -> str:
        """
        Return a token for a data-modifying API action.

        In general, this will be a CSRF token, unless *action* is in a special list of
        non-CSRF tokens. Tokens are cached for the session (until :meth:`_login` is
        called again); set *force* to ``True`` to force a new token to be fetched.

        Raises :exc:`.APIError` if there was an API issue.
        """
        if action not in self.SPECIAL_TOKENS:
            action = "csrf"
        if action in self._tokens and not force:
            return self._tokens[action]

        res = self.api_query(action="query", meta="tokens", type=action)
        if action not in self._tokens:
            err = "Tried to fetch a {0} token, but API returned: {1}"
            raise exceptions.APIError(err.format(action, res))
        return self._tokens[action]

    @typing.overload
    def namespace_id_to_name(self, ns_id: int, all: Literal[False] = False) -> str: ...

    @typing.overload
    def namespace_id_to_name(self, ns_id: int, all: Literal[True]) -> list[str]: ...

    def namespace_id_to_name(self, ns_id: int, all: bool = False) -> str | list[str]:
        """
        Given a namespace ID, returns associated namespace names.

        If *all* is ``False`` (default), we'll return the first name in the list, which
        is usually the localized version. Otherwise, we'll return the entire list,
        which includes the canonical name. For example, this returns ``"Wikipedia"``
        if *ns_id* = ``4`` and *all* is ``False`` on ``enwiki``; returns
        ``["Wikipedia", "Project", "WP"]`` if *ns_id* = ``4`` and *all* is ``True``.

        Raises :py:exc:`~earwigbot.exceptions.NamespaceNotFoundError` if the ID is
        not found.
        """
        try:
            if all:
                return self.namespaces[ns_id]
            else:
                return self.namespaces[ns_id][0]
        except KeyError:
            e = f"There is no namespace with id {ns_id}."
            raise exceptions.NamespaceNotFoundError(e)

    def namespace_name_to_id(self, name: str) -> int:
        """
        Given a namespace name, returns the associated ID.

        Like :py:meth:`namespace_id_to_name`, but reversed. Case is ignored, because
        namespaces are assumed to be case-insensitive.

        Raises :py:exc:`~earwigbot.exceptions.NamespaceNotFoundError` if the name is
        not found.
        """
        lname = name.lower()
        for ns_id, names in self.namespaces.items():
            lnames = [n.lower() for n in names]  # Be case-insensitive
            if lname in lnames:
                return ns_id

        e = f"There is no namespace with name '{name}'."
        raise exceptions.NamespaceNotFoundError(e)

    def get_page(
        self, title: str, follow_redirects: bool = False, pageid: int | None = None
    ) -> Page:
        """
        Return a :py:class:`Page` object for the given title.

        *follow_redirects* is passed directly to :py:class:`~earwigbot.wiki.page.Page`'s
        constructor. Also, this will return a
        :py:class:`~earwigbot.wiki.category.Category` object instead if the given title
        is in the category namespace. As :py:class:`~earwigbot.wiki.category.Category`
        is a subclass of :py:class:`~earwigbot.wiki.page.Page`, this should not
        cause problems.

        Note that this doesn't do any direct checks for existence or
        redirect-following: :py:class:`~earwigbot.wiki.page.Page`'s methods
        provide that.
        """
        prefixes = self.namespace_id_to_name(constants.NS_CATEGORY, all=True)
        prefix = title.split(":", 1)[0]
        if prefix != title:  # Avoid a page that is simply "Category"
            if prefix in prefixes:
                return Category(self, title, follow_redirects, pageid, self._logger)
        return Page(self, title, follow_redirects, pageid, self._logger)

    def get_category(
        self, catname: str, follow_redirects: bool = False, pageid: int | None = None
    ) -> Category:
        """
        Return a :py:class:`Category` object for the given category name.

        *catname* should be given *without* a namespace prefix. This method is really
        just shorthand for :py:meth:`get_page("Category:" + catname) <get_page>`.
        """
        prefix = self.namespace_id_to_name(constants.NS_CATEGORY)
        pagename = ":".join((prefix, catname))
        return Category(self, pagename, follow_redirects, pageid, self._logger)

    def get_user(self, username: str | None = None) -> User:
        """
        Return a :py:class:`User` object for the given username.

        If *username* is left as ``None``, then a :py:class:`~earwigbot.wiki.user.User`
        object representing the currently logged-in (or anonymous!) user is returned.
        """
        if not username:
            username = self._get_username()
        return User(self, username, self._logger)

    def delegate(
        self, services: dict[Service, Callable[P, T]], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        """
        Delegate a task to either the API or SQL depending on conditions.

        *services* should be a dictionary in which the key is the service name
        (:py:attr:`self.SERVICE_API <SERVICE_API>` or
        :py:attr:`self.SERVICE_SQL <SERVICE_SQL>`), and the value is the function to
        call for this service. All functions will be passed the same arguments the
        tuple *args* and the dict *kwargs*, which are both empty by default. The
        service order is determined by :py:meth:`_get_service_order`.

        Not every service needs an entry in the dictionary. Will raise
        :py:exc:`~earwigbot.exceptions.NoServiceError` if an appropriate service cannot
        be found.
        """
        order = self._get_service_order()
        for srv in order:
            if srv in services:
                try:
                    return services[srv](*args, **kwargs)
                except exceptions.ServiceError:
                    continue
        raise exceptions.NoServiceError(services)
