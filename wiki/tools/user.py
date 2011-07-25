# -*- coding: utf-8  -*-

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
        # Public attributes
        self.site = site  # Site instance, for doing API queries, etc
        self.name = name  # our username

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

    def _get_attribute_from_api(self, attr, force):
        """
        Docstring needed
        """
        if self._exists is None or force:
            self._load_attributes_from_api()
        if self._exists is False:
            raise UserNotFoundError(self.name)
        return getattr(self, attr)

    def _load_attributes_from_api(self):
        """
        Docstring needed
        """
        params = {"action": "query", "list": "users", "ususers": self.name,
        "usprop": "blockinfo|groups|rights|editcount|registration|emailable|gender"}
        result = self.site.api_query(params)

        # normalize our username in case it was entered oddly
        self.name = result["query"]["users"][0]["name"]

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

    def exists(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_exists", force)

    def get_userid(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_userid", force)

    def get_blockinfo(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_blockinfo", force)

    def get_groups(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_groups", force)

    def get_rights(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_rights", force)

    def get_editcount(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_editcount", force)

    def get_registration(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_registration", force)

    def get_emailable(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_emailable", force)

    def get_gender(self, force=False):
        """
        Docstring needed
        """
        return self._get_attribute_from_api("_gender", force)

    def get_userpage(self):
        """
        Docstring needed
        """
        return Page(self.site, "User:" + self.name)  # Namespace checking!

    def get_talkpage(self):
        """
        Docstring needed
        """
        return Page(self.site, "User talk:" + self.name)  # Namespace checking!
