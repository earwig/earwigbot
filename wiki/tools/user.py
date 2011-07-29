# -*- coding: utf-8  -*-

from wiki.tools.constants import *
from wiki.tools.exceptions import UserNotFoundError
from wiki.tools.page import Page

class User(object):
    """
    EarwigBot's Wiki Toolset: User Class
    """

    def __init__(self, site, name):
        """
        Docstring needed
        """
        # Site instance, for doing API queries, etc
        self.site = site

        # Username
        self._name = name

        # Attributes filled in by an API query
        self._exists = None
        self._userid = None
        self._blockinfo = None
        self._groups = None
        self._rights = None
        self._editcount = None
        self._registration = None
        self._emailable = None
        self._gender = None

    def _get_attribute(self, attr, force, raise_exception=True):
        """
        Docstring needed
        """
        if self._exists is None or force:
            self._load_attributes()
        if self._exists is False and raise_exception:
            e = "User '{0}' does not exist.".format(self._name)
            raise UserNotFoundError(e)
        return getattr(self, attr)

    def _load_attributes(self):
        """
        Docstring needed
        """
        params = {"action": "query", "list": "users", "ususers": self._name,
        "usprop": "blockinfo|groups|rights|editcount|registration|emailable|gender"}
        result = self.site.api_query(params)

        # normalize our username in case it was entered oddly
        self._name = result["query"]["users"][0]["name"]

        try:
            self._userid = result["query"]["users"][0]["userid"]
        except KeyError:  # userid is missing, so user does not exist
            self._exists = False
            return

        self._exists = True
        res = result['query']['users'][0]

        self._groups = res["groups"]
        self._rights = res["rights"]
        self._editcount = res["editcount"]
        self._registration = res["registration"]
        self._gender = res["gender"]

        try:
            res["emailable"]
        except KeyError:
            self._emailable = False
        else:
            self._emailable = True

        try:
            self._blockinfo = {"by": res["blockedby"],
                "reason": res["blockreason"], "expiry": res["blockexpiry"]}
        except KeyError:
            self._blockinfo = False

    def name(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_name", force, raise_exception=False)

    def exists(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_exists", force, raise_exception=False)

    def userid(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_userid", force)

    def blockinfo(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_blockinfo", force)

    def groups(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_groups", force)

    def rights(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_rights", force)

    def editcount(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_editcount", force)

    def registration(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_registration", force)

    def is_emailable(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_emailable", force)

    def gender(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute("_gender", force)

    def userpage(self):
        """
        Docstring needed
        """
        prefix = self.site.namespace_id_to_name(NS_USER)
        pagename = "{0}:{1}".format(prefix, self._name)
        return Page(self.site, pagename)

    def talkpage(self):
        """
        Docstring needed
        """
        prefix = self.site.namespace_id_to_name(NS_USER_TALK)
        pagename = "{0}:{1}".format(prefix, self._name)
        return Page(self.site, pagename)
