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

    def __init__(self, name, project, lang, api=None, sql=(None, None)):
        """
        Docstring needed
        """
        self.name = name
        self.project = project
        self.lang = lang
        self._api = api
        self._sql = sql
        
        self._namespaces = None

    def _get_namespaces_from_api(self):
        """
        Docstring needed
        """
        params = {"action": "query", "meta": "siteinfo",
            "siprop": "namespaces|namespacealiases"}
        result = self.api_query(params)
        
        if self._namespaces is None:
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
        params["format"] = "json"
        data = urlencode(params)
        result = urlopen(self._api, data).read()
        return loads(result)

    def namespaces(self):
        """
        Docstring needed
        """
        if self._namespaces is None:
            self._get_namespaces_from_api()
        
        return self._namespaces

    def namespace_id_to_name(self, ns_id, all=False):
        """
        Docstring needed
        """
        if self._namespaces is None:
            self._get_namespaces_from_api()

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
        if self._namespaces is None:
            self._get_namespaces_from_api()
        
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
