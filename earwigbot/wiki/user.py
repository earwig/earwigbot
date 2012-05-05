# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from time import gmtime, strptime

from earwigbot.exceptions import UserNotFoundError
from earwigbot.wiki import constants
from earwigbot.wiki.page import Page

__all__ = ["User"]

class User(object):
    """
    EarwigBot's Wiki Toolset: User Class

    Represents a User on a given Site. Has methods for getting a bunch of 
    information about the user, such as editcount and user rights, methods for
    returning the user's userpage and talkpage, etc.

    Attributes:
    name         -- the user's username
    exists       -- True if the user exists, or False if they do not
    userid       -- an integer ID representing the user
    blockinfo    -- information about any current blocks on the user
    groups       -- a list of the user's groups
    rights       -- a list of the user's rights
    editcount    -- the number of edits made by the user
    registration -- the time the user registered as a time.struct_time
    emailable    -- True if you can email the user, False if you cannot
    gender       -- the user's gender ("male", "female", or "unknown")

    Public methods:
    reload       -- forcibly reload the user's attributes
    get_userpage -- returns a Page object representing the user's userpage
    get_talkpage -- returns a Page object representing the user's talkpage
    """

    def __init__(self, site, name):
        """Constructor for new User instances.

        Takes two arguments, a Site object (necessary for doing API queries),
        and the name of the user, preferably without "User:" in front, although
        this prefix will be automatically removed by the API if given.

        You can also use site.get_user() instead, which returns a User object,
        and is preferred.

        We won't do any API queries yet for basic information about the user -
        save that for when the information is requested.
        """
        self._site = site
        self._name = name

    def __repr__(self):
        """Returns the canonical string representation of the User."""
        return "User(name={0!r}, site={1!r})".format(self._name, self._site)

    def __str__(self):
        """Returns a nice string representation of the User."""
        return '<User "{0}" of {1}>'.format(self.name(), str(self._site))

    def _get_attribute(self, attr, force):
        """Internally used to get an attribute by name.

        We'll call _load_attributes() to get this (and all other attributes)
        from the API if it is not already defined. If `force` is True, we'll
        re-load them even if they've already been loaded.

        Raises UserNotFoundError if a nonexistant user prevents us from
        returning a certain attribute.
        """
        if not hasattr(self, attr) or force:
            self._load_attributes()
        if self._exists is False:
            e = "User '{0}' does not exist.".format(self._name)
            raise UserNotFoundError(e)
        return getattr(self, attr)

    def _load_attributes(self):
        """Internally used to load all attributes from the API.

        Normally, this is called by _get_attribute() when a requested attribute
        is not defined. This defines it.
        """
        params = {"action": "query", "list": "users", "ususers": self._name,
                  "usprop": "blockinfo|groups|rights|editcount|registration|emailable|gender"}
        result = self._site._api_query(params)
        res = result["query"]["users"][0]

        # normalize our username in case it was entered oddly
        self._name = res["name"]

        try:
            self._userid = res["userid"]
        except KeyError:  # userid is missing, so user does not exist
            self._exists = False
            return

        self._exists = True

        try:
            self._blockinfo = {
                "by": res["blockedby"],
                "reason": res["blockreason"],
                "expiry": res["blockexpiry"]
            }
        except KeyError:
            self._blockinfo = False

        self._groups = res["groups"]
        try:
            self._rights = res["rights"].values()
        except AttributeError:
            self._rights = res["rights"]
        self._editcount = res["editcount"]

        reg = res["registration"]
        try:
            self._registration = strptime(reg, "%Y-%m-%dT%H:%M:%SZ")
        except TypeError:
            # Sometimes the API doesn't give a date; the user's probably really
            # old. There's nothing else we can do!
            self._registration = gmtime(0)

        try:
            res["emailable"]
        except KeyError:
            self._emailable = False
        else:
            self._emailable = True

        self._gender = res["gender"]

    def name(self, force=False):
        """Returns the user's name.

        If `force` is True, we will load the name from the API and return that.
        This could potentially return a "normalized" version of the name - for
        example, without a "User:" prefix or without underscores. Unlike other
        attribute getters, this will never make an API query without `force`.

        Note that if another attribute getter, like exists(), has already been
        called, then the username has already been normalized.
        """
        if force:
            self._load_attributes()
        return self._name

    def exists(self, force=False):
        """Returns True if the user exists, or False if they do not.

        Makes an API query if `force` is True or if we haven't made one
        already.
        """
        if not hasattr(self, "_exists") or force:
            self._load_attributes()
        return self._exists

    def userid(self, force=False):
        """Returns an integer ID used by MediaWiki to represent the user.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_userid", force)

    def blockinfo(self, force=False):
        """Returns information about a current block on the user.

        If the user is not blocked, returns False. If they are, returns a dict
        with three keys: "by" is the blocker's username, "reason" is the reason
        why they were blocked, and "expiry" is when the block expires.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_blockinfo", force)

    def groups(self, force=False):
        """Returns a list of groups this user is in, including "*".

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_groups", force)

    def rights(self, force=False):
        """Returns a list of this user's rights.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_rights", force)

    def editcount(self, force=False):
        """Returns the number of edits made by the user.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_editcount", force)

    def registration(self, force=False):
        """Returns the time the user registered as a time.struct_time object.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_registration", force)

    def emailable(self, force=False):
        """Returns True if the user can be emailed, or False if they cannot.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_emailable", force)

    def gender(self, force=False):
        """Returns the user's gender.

        Can return either "male", "female", or "unknown", if they did not
        specify it.

        Raises UserNotFoundError if the user does not exist. Makes an API query
        if `force` is True or if we haven't made one already.
        """
        return self._get_attribute("_gender", force)

    def get_userpage(self):
        """Returns a Page object representing the user's userpage.
        
        No checks are made to see if it exists or not. Proper site namespace
        conventions are followed.
        """
        prefix = self._site.namespace_id_to_name(constants.NS_USER)
        pagename = ':'.join((prefix, self._name))
        return Page(self._site, pagename)

    def get_talkpage(self):
        """Returns a Page object representing the user's talkpage.
        
        No checks are made to see if it exists or not. Proper site namespace
        conventions are followed.
        """
        prefix = self._site.namespace_id_to_name(constants.NS_USER_TALK)
        pagename = ':'.join((prefix, self._name))
        return Page(self._site, pagename)
