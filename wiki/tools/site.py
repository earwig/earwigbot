# -*- coding: utf-8  -*-

from json import loads
from urllib import urlencode
from urllib2 import urlopen

from wiki.tools.category import Category
from wiki.tools.constants import *
from wiki.tools.exceptions import NamespaceNotFoundError
from wiki.tools.page import Page
from wiki.tools.user import User

class Site(object):
    """
    EarwigBot's Wiki Toolset: Site Class
    """

    def __init__(self, name=None, project=None, lang=None, base_url=None,
            article_path=None, script_path=None, sql=(None, None),
            namespaces=None):
        """
        Docstring needed
        """
        self._name = name
        self._project = project
        self._lang = lang
        self._base_url = base_url
        self._article_path = article_path
        self._script_path = script_path
        self._sql = sql
        self._namespaces = namespaces

        # get all of the above attributes that were not specified by the user
        self._load_attributes()

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

        if self._name is None or force:
            self._name = res["wikiid"]

        if self._project is None or force:
            self._project = res["sitename"].lower()

        if self._lang is None or force:
            self._lang = res["lang"]

        if self._base_url is None or force:
            self._base_url = res["server"]

        if self._article_path is None or force:
            self._article_path = res["articlepath"]

        if self._script_path is None or force:
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

    def api_query(self, params):
        """
        Docstring needed
        """
        url = ''.join((self._base_url, self._script_path, "/api.php"))
        params["format"] = "json"
        data = urlencode(params)
        result = urlopen(url, data).read()
        return loads(result)

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

    def base_url(self):
        """
        Docstring needed
        """
        return self._base_url

    def article_path(self):
        """
        Docstring needed
        """
        return self._article_path

    def script_path(self):
        """
        Docstring needed
        """
        return self._script_path

    def namespaces(self):
        """
        Docstring needed
        """
        return self._namespaces

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

    def get_user(self, username):
        """
        Docstring needed
        """
        return User(self, username)
