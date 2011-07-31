# -*- coding: utf-8  -*-

from cookielib import CookieJar
from json import loads
from re import escape as re_escape, match as re_match
from urllib import unquote_plus, urlencode
from urllib2 import build_opener, HTTPCookieProcessor, URLError
from urlparse import urlparse

from wiki.tools.category import Category
from wiki.tools.constants import *
from wiki.tools.exceptions import *
from wiki.tools.page import Page
from wiki.tools.user import User

class Site(object):
    """
    EarwigBot's Wiki Toolset: Site Class
    """

    def __init__(self, name=None, project=None, lang=None, base_url=None,
            article_path=None, script_path=None, sql=(None, None),
            namespaces=None, login=(None, None), cookiejar=None):
        """
        Docstring needed
        """
        # attributes referring to site information, filled in by an API query
        # if they are missing (and an API url can be determined)
        self._name = name
        self._project = project
        self._lang = lang
        self._base_url = base_url
        self._article_path = article_path
        self._script_path = script_path
        self._sql = sql
        self._namespaces = namespaces

        # set up cookiejar and URL opener for making API queries
        if cookiejar is not None:
            self._cookiejar = cookiejar
        else:
            self._cookiejar = CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookiejar))
        self._opener.addheaders = [('User-agent', USER_AGENT)]

        # get all of the above attributes that were not specified as arguments
        self._load_attributes()

        # if we have a name/pass and the API says we're not logged in, log in
        self._login_info = name, password = login
        if name is not None and password is not None:
            logged_in_as = self._get_username_from_cookies()
            if logged_in_as is None or name != logged_in_as:
                self._login(login)

    def _load_attributes(self, force=False):
        """
        Docstring needed
        """
        # all attributes to be loaded, except _namespaces, which is a special
        # case because it requires additional params in the API query
        attrs = [self._name, self._project, self._lang, self._base_url,
            self._article_path, self._script_path]

        params = {"action": "query", "meta": "siteinfo"}

        if self._namespaces is None or force:
            params["siprop"] = "general|namespaces|namespacealiases"
            result = self.api_query(params)
            self._load_namespaces(result)
        elif all(attrs):  # everything is already specified and we're not told
            return        # to force a reload, so do nothing
        else:  # we're only loading attributes other than _namespaces
            params["siprop"] = "general"
            result = self.api_query(params)

        res = result["query"]["general"]
        self._name = res["wikiid"]
        self._project = res["sitename"].lower()
        self._lang = res["lang"]
        self._base_url = res["server"]
        self._article_path = res["articlepath"]
        self._script_path = res["scriptpath"]

    def _load_namespaces(self, result):
        """
        Docstring needed
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
        """Return the cookie `name` in `domain`, unless it is expired. Return
        None if no cookie was found.
        """
        for cookie in self._cookiejar:
            if cookie.name == name and cookie.domain == domain:
                if cookie.is_expired():
                    break
                return cookie
        return None

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
            # build a regex that will match domains this cookie affects
            search = ''.join(("(.*?)", re_escape(cookie.domain)))
            if re_match(search, domain):  # test it against our site
                user_name = self._get_cookie("centralauth_User", cookie.domain)
                if user_name is not None:
                    return user_name.value

        return None

    def _get_username_from_api(self):
        """Do a simple API query to get our username and return it.
        
        This is a reliable way to make sure we are actually logged in, because
        it doesn't deal with annoying cookie logic, but it results in an API
        query that is unnecessary in many cases.
        
        Called by _get_username() (in turn called by get_user() with no
        username argument) when cookie lookup fails, probably indicating that
        we are logged out.
        """
        params = {"action": "query", "meta": "userinfo"}
        result = self.api_query(params)
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
        """
        Docstring needed
        """
        name, password = login
        params = {"action": "login", "lgname": name, "lgpassword": password}
        if token is not None:
            params["lgtoken"] = token
        result = self.api_query(params)
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
        """
        Docstring needed
        """
        params = {"action": "logout"}
        self.api_query(params)
        self._cookiejar.clear()
        self._save_cookiejar()

    def api_query(self, params):
        """
        Docstring needed
        """
        if self._base_url is None or self._script_path is None:
            e = "Tried to do an API query, but no API URL is known."
            raise SiteAPIError(e)

        url = ''.join((self._base_url, self._script_path, "/api.php"))
        params["format"] = "json"  # this is the only format we understand
        data = urlencode(params)

        print url, data  # debug code

        try:
            response = self._opener.open(url, data)
        except URLError as error:
            if hasattr(error, "reason"):
                e = "API query at {0} failed because {1}."
                e = e.format(error.geturl, error.reason)
            elif hasattr(error, "code"):
                e = "API query at {0} failed; got an error code of {1}."
                e = e.format(error.geturl, error.code)
            else:
                e = "API query failed."
            raise SiteAPIError(e)
        else:
            result = response.read()
            return loads(result)  # parse as a JSON object

    def name(self):
        """
        Docstring needed
        """
        return self._name

    def project(self):
        """
        Docstring needed
        """
        return self._project

    def lang(self):
        """
        Docstring needed
        """
        return self._lang

    def domain(self):
        """
        Docstring needed
        """
        return urlparse(self._base_url).netloc

    def namespace_id_to_name(self, ns_id, all=False):
        """
        Docstring needed
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
        """
        Docstring needed
        """
        lname = name.lower()
        for ns_id, names in self._namespaces.items():
            lnames = [n.lower() for n in names]  # be case-insensitive
            if lname in lnames:
                return ns_id

        e = "There is no namespace with name '{0}'.".format(name)
        raise NamespaceNotFoundError(e)

    def get_page(self, pagename):
        """
        Docstring needed
        """
        prefixes = self.namespace_id_to_name(NS_CATEGORY, all=True)
        prefix = pagename.split(":", 1)[0]
        if prefix != pagename:  # avoid a page that is simply "Category"
            if prefix in prefixes:
                return Category(self, pagename)
        return Page(self, pagename)

    def get_category(self, catname):
        """
        Docstring needed
        """
        prefix = self.namespace_id_to_name(NS_CATEGORY)
        pagename = "{0}:{1}".format(prefix, catname)
        return Category(self, pagename)

    def get_user(self, username=None):
        """
        Docstring needed
        """
        if username is None:
            username = self._get_username()
        return User(self, username)
