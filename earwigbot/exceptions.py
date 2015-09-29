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

"""
**EarwigBot: Exceptions**

This module contains all exceptions used by EarwigBot::

    EarwigBotError
     +-- NoConfigError
     +-- IRCError
     |    +-- BrokenSocketError
     +-- WikiToolsetError
          +-- SiteNotFoundError
          +-- ServiceError
          |    +-- APIError
          |    +-- SQLError
          +-- NoServiceError
          +-- LoginError
          +-- PermissionsError
          +-- NamespaceNotFoundError
          +-- PageNotFoundError
          +-- InvalidPageError
          +-- RedirectError
          +-- UserNotFoundError
          +-- EditError
          |    +-- EditConflictError
          |    +-- NoContentError
          |    +-- ContentTooBigError
          |    +-- SpamDetectedError
          |    +-- FilteredError
          +-- CopyvioCheckError
               +-- UnknownSearchEngineError
               +-- UnsupportedSearchEngineError
               +-- SearchQueryError
               +-- ParserExclusionError
"""

class EarwigBotError(Exception):
    """Base exception class for errors in EarwigBot."""

class NoConfigError(EarwigBotError):
    """The bot cannot be run without a config file.

    This occurs if no config file exists, and the user said they did not want
    one to be created.
    """

class IRCError(EarwigBotError):
    """Base exception class for errors in IRC-relation sections of the bot."""

class BrokenSocketError(IRCError):
    """A socket has broken, because it is not sending data.

    Raised by :py:meth:`IRCConnection._get
    <earwigbot.irc.connection.IRCConnection._get>`.
    """

class WikiToolsetError(EarwigBotError):
    """Base exception class for errors in the Wiki Toolset."""

class SiteNotFoundError(WikiToolsetError):
    """A particular site could not be found in the sites database.

    Raised by :py:class:`~earwigbot.wiki.sitesdb.SitesDB`.
    """

class ServiceError(WikiToolsetError):
    """Base exception class for an error within a service (the API or SQL).

    This is caught by :py:meth:`Site.delegate
    <earwigbot.wiki.site.Site.delegate>` to indicate a service is
    non-functional so another, less-preferred one can be tried.
    """

class APIError(ServiceError):
    """Couldn't connect to a site's API.

    Perhaps the server doesn't exist, our URL is wrong or incomplete, or
    there are temporary problems on their end.

    Raised by :py:meth:`Site.api_query <earwigbot.wiki.site.Site.api_query>`.
    """

class SQLError(ServiceError):
    """Some error involving SQL querying occurred.

    Raised by :py:meth:`Site.sql_query <earwigbot.wiki.site.Site.sql_query>`.
    """

class NoServiceError(WikiToolsetError):
    """No service is functioning to handle a specific task.

    Raised by :py:meth:`Site.delegate <earwigbot.wiki.site.Site.delegate>`.
    """

class LoginError(WikiToolsetError):
    """An error occured while trying to login.

    Perhaps the username/password is incorrect.

    Raised by :py:meth:`Site._login <earwigbot.wiki.site.Site._login>`.
    """

class PermissionsError(WikiToolsetError):
    """A permissions error ocurred.

    We tried to do something we don't have permission to, like trying to delete
    a page as a non-admin, or trying to edit a page without login information
    and AssertEdit enabled. This will also be raised if we have been blocked
    from editing.

    Raised by :py:meth:`Page.edit <earwigbot.wiki.page.Page.edit>`,
    :py:meth:`Page.add_section <earwigbot.wiki.page.Page.add_section>`, and
    other API methods depending on settings.
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

class CopyvioCheckError(WikiToolsetError):
    """An error occured when checking a page for copyright violations.

    This is a base class for multiple exceptions; usually one of those will be
    raised instead of this.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_check>` and
    :py:meth:`Page.copyvio_compare
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_compare>`.
    """

class UnknownSearchEngineError(CopyvioCheckError):
    """Attempted to do a copyvio check with an unknown search engine.

    Search engines are specified in :file:`config.yml` as
    :py:attr:`config.wiki["search"]["engine"]`.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_check>`.
    """

class UnsupportedSearchEngineError(CopyvioCheckError):
    """Attmpted to do a copyvio check using an unavailable engine.

    This might occur if, for example, an engine requires oauth2 but the package
    couldn't be imported.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_check>`.
    """

class SearchQueryError(CopyvioCheckError):
    """Some error ocurred while doing a search query.

    Raised by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_check>`.
    """

class ParserExclusionError(CopyvioCheckError):
    """A content parser detected that the given source should be excluded.

    Raised internally by :py:meth:`Page.copyvio_check
    <earwigbot.wiki.copyvios.CopyvioMixIn.copyvio_check>`; should not be
    exposed in client code.
    """
