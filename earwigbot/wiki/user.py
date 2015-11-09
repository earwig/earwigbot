# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from logging import getLogger, NullHandler
from time import gmtime, strptime
from socket import AF_INET, AF_INET6, error as socket_error, inet_pton

from earwigbot.exceptions import UserNotFoundError
from earwigbot.wiki import constants
from earwigbot.wiki.page import Page

__all__ = ["User"]

class User(object):
    """
    **EarwigBot: Wiki Toolset: User**

    Represents a user on a given :py:class:`~earwigbot.wiki.site.Site`. Has
    methods for getting a bunch of information about the user, such as
    editcount and user rights, methods for returning the user's userpage and
    talkpage, etc.

    *Attributes:*

    - :py:attr:`site`:         the user's corresponding Site object
    - :py:attr:`name`:         the user's username
    - :py:attr:`exists`:       ``True`` if the user exists, else ``False``
    - :py:attr:`userid`:       an integer ID representing the user
    - :py:attr:`blockinfo`:    information about any current blocks on the user
    - :py:attr:`groups`:       a list of the user's groups
    - :py:attr:`rights`:       a list of the user's rights
    - :py:attr:`editcount`:    the number of edits made by the user
    - :py:attr:`registration`: the time the user registered
    - :py:attr:`emailable`:    ``True`` if you can email the user, or ``False``
    - :py:attr:`gender`:       the user's gender ("male"/"female"/"unknown")
    - :py:attr:`is_ip`:        ``True`` if this is an IP address, or ``False``

    *Public methods:*

    - :py:meth:`reload`:       forcibly reloads the user's attributes
    - :py:meth:`get_userpage`: returns a Page object representing the user's
      userpage
    - :py:meth:`get_talkpage`: returns a Page object representing the user's
      talkpage
    """

    def __init__(self, site, name, logger=None):
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

        # Set up our internal logger:
        if logger:
            self._logger = logger
        else:  # Just set up a null logger to eat up our messages:
            self._logger = getLogger("earwigbot.wiki")
            self._logger.addHandler(NullHandler())

    def __repr__(self):
        """Return the canonical string representation of the User."""
        return "User(name={0!r}, site={1!r})".format(self._name, self._site)

    def __str__(self):
        """Return a nice string representation of the User."""
        return '<User "{0}" of {1}>'.format(self.name, str(self.site))

    def _get_attribute(self, attr):
        """Internally used to get an attribute by name.

        We'll call _load_attributes() to get this (and all other attributes)
        from the API if it is not already defined.

        Raises UserNotFoundError if a nonexistant user prevents us from
        returning a certain attribute.
        """
        if not hasattr(self, attr):
            self._load_attributes()
        if not self._exists:
            e = u"User '{0}' does not exist.".format(self._name)
            raise UserNotFoundError(e)
        return getattr(self, attr)

    def _load_attributes(self):
        """Internally used to load all attributes from the API.

        Normally, this is called by _get_attribute() when a requested attribute
        is not defined. This defines it.
        """
        props = "blockinfo|groups|rights|editcount|registration|emailable|gender"
        result = self.site.api_query(action="query", list="users",
                                     ususers=self._name, usprop=props)
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

    @property
    def site(self):
        """The user's corresponding Site object."""
        return self._site

    @property
    def name(self):
        """The user's username.

        This will never make an API query on its own, but if one has already
        been made by the time this is retrieved, the username may have been
        "normalized" from the original input to the constructor, converted into
        a Unicode object, with underscores removed, etc.
        """
        return self._name

    @property
    def exists(self):
        """``True`` if the user exists, or ``False`` if they do not.

        Makes an API query only if we haven't made one already.
        """
        if not hasattr(self, "_exists"):
            self._load_attributes()
        return self._exists

    @property
    def userid(self):
        """An integer ID used by MediaWiki to represent the user.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_userid")

    @property
    def blockinfo(self):
        """Information about any current blocks on the user.

        If the user is not blocked, returns ``False``. If they are, returns a
        dict with three keys: ``"by"`` is the blocker's username, ``"reason"``
        is the reason why they were blocked, and ``"expiry"`` is when the block
        expires.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_blockinfo")

    @property
    def groups(self):
        """A list of groups this user is in, including ``"*"``.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_groups")

    @property
    def rights(self):
        """A list of this user's rights.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_rights")

    @property
    def editcount(self):
        """Returns the number of edits made by the user.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_editcount")

    @property
    def registration(self):
        """The time the user registered as a :py:class:`time.struct_time`.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_registration")

    @property
    def emailable(self):
        """``True`` if the user can be emailed, or ``False`` if they cannot.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_emailable")

    @property
    def gender(self):
        """The user's gender.

        Can return either ``"male"``, ``"female"``, or ``"unknown"``, if they
        did not specify it.

        Raises :py:exc:`~earwigbot.exceptions.UserNotFoundError` if the user
        does not exist. Makes an API query only if we haven't made one already.
        """
        return self._get_attribute("_gender")

    @property
    def is_ip(self):
        """``True`` if the user is an IP address, or ``False`` otherwise.

        This tests for IPv4 and IPv6 using :py:func:`socket.inet_pton` on the
        username. No API queries are made.
        """
        try:
            inet_pton(AF_INET, self.name)
        except socket_error:
            try:
                inet_pton(AF_INET6, self.name)
            except socket_error:
                return False
        return True

    def reload(self):
        """Forcibly reload the user's attributes.

        Emphasis on *reload*: this is only necessary if there is reason to
        believe they have changed.
        """
        self._load_attributes()

    def get_userpage(self):
        """Return a Page object representing the user's userpage.

        No checks are made to see if it exists or not. Proper site namespace
        conventions are followed.
        """
        prefix = self.site.namespace_id_to_name(constants.NS_USER)
        pagename = ':'.join((prefix, self._name))
        return Page(self.site, pagename)

    def get_talkpage(self):
        """Return a Page object representing the user's talkpage.

        No checks are made to see if it exists or not. Proper site namespace
        conventions are followed.
        """
        prefix = self.site.namespace_id_to_name(constants.NS_USER_TALK)
        pagename = ':'.join((prefix, self._name))
        return Page(self.site, pagename)
