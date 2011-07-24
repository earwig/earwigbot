# -*- coding: utf-8  -*-

from json import loads
from urllib import urlencode
from urllib2 import urlopen

from wiki.tools.category import Category
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

    def api_query(self, params):
        """
        Docstring needed
        """
        params["format"] = "json"
        data = urlencode(params)
        result = urlopen(self._api, data).read()
        return loads(result)

    def get_page(self, pagename):
        """
        Docstring needed
        """
        if pagename.startswith("Category:"):  # proper namespace checking!
            return get_category(pagename[9:])
        return Page(self, pagename)

    def get_category(self, catname):
        """
        Docstring needed
        """
        return Category(self, "Category:" + catname)  # namespace checking!

    def get_user(self, username):
        """
        Docstring needed
        """
        return User(self, username)
