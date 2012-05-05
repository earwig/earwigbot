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

"""
EarwigBot Exceptions

This module contains all exceptions used by EarwigBot::

    EarwigBotError
     +-- IRCError
     |    +-- BrokenSocketError
     |    +-- KwargParseError
     +-- WikiToolsetError
          +-- SiteNotFoundError
          +-- SiteAPIError
          +-- LoginError
          +-- NamespaceNotFoundError
          +-- PageNotFoundError
          +-- InvalidPageError
          +-- RedirectError
          +-- UserNotFoundError
          +-- EditError
          |    +-- PermissionsError
          |    +-- EditConflictError
          |    +-- NoContentError
          |    +-- ContentTooBigError
          |    +-- SpamDetectedError
          |    +-- FilteredError
          +-- SQLError
          +-- CopyvioCheckError
               +-- UnknownSearchEngineError
               +-- UnsupportedSearchEngineError
               +-- SearchQueryError
"""

class EarwigBotError(Exception):
    """Base exception class for errors in EarwigBot."""

class IRCError(EarwigBotError):
    """Base exception class for errors in IRC-relation sections of the bot."""

class BrokenSocketError(IRCError):
    """A socket has broken, because it is not sending data.

    Raised by :py:meth:`IRCConnection._get
    <earwigbot.irc.connection.IRCConnection._get>`.
    """

class KwargParseError(IRCError):
    """Couldn't parse a certain keyword argument in an IRC message.
    
    This is usually caused by it being given incorrectly: e.g., no value (abc),
    just a value (=xyz), just an equal sign (=), instead of the correct form
    (abc=xyz).

    Raised by :py:meth:`Data.parse_kwargs
    <earwigbot.irc.data.Data.parse_kwargs>`.
    """

class WikiToolsetError(EarwigBotError):
    """Base exception class for errors in the Wiki Toolset."""

class SiteNotFoundError(WikiToolsetError):
    """A particular site could not be found in the sites database.

    Raised by :py:class:`~earwigbot.wiki.sitesdb.SitesDB`.
    """

class SiteAPIError(WikiToolsetError):
    """Couldn't connect to a site's API.

    Perhaps the server doesn't exist, our URL is wrong or incomplete, or
    there are temporary problems on their end.

    Raised by :py:meth:`Site.api_query <earwigbot.wiki.site.Site.api_query>`.
    """

class LoginError(WikiToolsetError):
    """An error occured while trying to login.

    Perhaps the username/password is incorrect.

    Raised by :py:meth:`Site._login <earwigbot.wiki.site.Site._login>`.
    """

class NamespaceNotFoundError(WikiToolsetError):
    """A requested namespace name or namespace ID does not exist.

    Raised by :py:meth:`Site.namespace_id_to_name
    <earwigbot.wiki.site.Site.namespace_id_to_name>` and
    :py:meth:`Site.namespace_name_to_id
    <earwigbot.wiki.site.Site.namespace_name_to_id>`.
    """

class PageNotFoundError(WikiToolsetError):
    """Attempted to get information about a page that does not exist.

    Raised by :py:class:`~earwigbot.wiki.page.Page`.
    """

class InvalidPageError(WikiToolsetError):
    """Attempted to get information about a page whose title is invalid.

    Raised by :py:class:`~earwigbot.wiki.page.Page`.
    """

class RedirectError(WikiToolsetError):
    """A redirect-only method was called on a malformed or non-redirect page.

    Raised by :py:meth:`Page.get_redirect_target
    <earwigbot.wiki.page.Page.get_redirect_target>`.
    """

class UserNotFoundError(WikiToolsetError):
    """Attempted to get certain information about a user that does not exist.

    Raised by :py:class:`~earwigbot.wiki.user.User`.
    """

class EditError(WikiToolsetError):
    """An error occured while editing.

    This is used as a base class for all editing errors; this one specifically
    is used only when a generic error occurs that we don't know about.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class PermissionsError(EditError):
    """A permissions error ocurred while editing.
    
    We tried to do something we don't have permission to, like trying to delete
    a page as a non-admin, or trying to edit a page without login information
    and AssertEdit enabled.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class EditConflictError(EditError):
    """We gotten an edit conflict or a (rarer) delete/recreate conflict.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class NoContentError(EditError):
    """We tried to create a page or new section with no content.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class ContentTooBigError(EditError):
    """The edit we tried to push exceeded the article size limit.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class SpamDetectedError(EditError):
    """The spam filter refused our edit.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class FilteredError(EditError):
    """The edit filter refused our edit.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>` and
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`.
    """

class SQLError(WikiToolsetError):
    """Some error involving SQL querying occurred.

    Raised by :py:meth:`Site.sql_query <earwigbot.wiki.site.Site.sql_query>`.
    """

class CopyvioCheckError(WikiToolsetError):
    """An error occured when checking a page for copyright violations.

    This is a base class for multiple exceptions; usually one of those will be
    raised instead of this.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check>` and
    :py:meth:`Page.copyvio_compare
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_compare>`.
    """

class UnknownSearchEngineError(CopyvioCheckError):
    """Attempted to do a copyvio check with an unknown search engine.

    Search engines are specified in :file:`config.yml` as
    :py:attr:`config.wiki["search"]["engine"]`.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check>` and
    :py:meth:`Page.copyvio_compare
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_compare>`.
    """

class UnsupportedSearchEngineError(CopyvioCheckError):
    """Attmpted to do a copyvio check using an unavailable engine.

    This might occur if, for example, an engine requires oauth2 but the package
    couldn't be imported.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check>` and
    :py:meth:`Page.copyvio_compare
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_compare>`.
    """

class SearchQueryError(CopyvioCheckError):
    """Some error ocurred while doing a search query.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check>` and
    :py:meth:`Page.copyvio_compare
    <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_compare>`.
    """
