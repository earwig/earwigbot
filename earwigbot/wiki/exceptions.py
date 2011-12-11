# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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
EarwigBot's Wiki Toolset: Exceptions

This module contains all exceptions used by the wiki package. There are a lot.
"""

class WikiToolsetError(Exception):
    """Base exception class for errors in the Wiki Toolset."""

class SiteNotFoundError(WikiToolsetError):
    """A site matching the args given to get_site() could not be found in the
    config file."""

class SiteAPIError(WikiToolsetError):
    """We couldn't connect to a site's API, perhaps because the server doesn't
    exist, our URL is wrong or incomplete, or they're having temporary
    problems."""

class LoginError(WikiToolsetError):
    """An error occured while trying to login. Perhaps the username/password is
    incorrect."""

class NamespaceNotFoundError(WikiToolsetError):
    """A requested namespace name or namespace ID does not exist."""

class PageNotFoundError(WikiToolsetError):
    """Attempting to get certain information about a page that does not
    exist."""

class InvalidPageError(WikiToolsetError):
    """Attempting to get certain information about a page whose title is
    invalid."""

class RedirectError(WikiToolsetError):
    """Page's get_redirect_target() method failed because the page is either
    not a redirect, or it is malformed."""

class UserNotFoundError(WikiToolsetError):
    """Attempting to get certain information about a user that does not
    exist."""

class EditError(WikiToolsetError):
    """We got some error while editing. Sometimes, a subclass of this exception
    will be used, like PermissionsError or EditConflictError."""

class PermissionsError(EditError):
    """We tried to do something we don't have permission to, like a non-admin
    trying to delete a page, or trying to edit a page when no login information
    was provided."""

class EditConflictError(EditError):
    """We've gotten an edit conflict or a (rarer) delete/recreate conflict."""

class NoContentError(EditError):
    """We tried to create a page or new section with no content."""

class ContentTooBigError(EditError):
    """The edit we tried to push exceeded the article size limit."""

class SpamDetectedError(EditError):
    """The spam filter refused our edit."""

class FilteredError(EditError):
    """The edit filter refused our edit."""

class SQLError(WikiToolsetError):
    """Some error involving SQL querying occurred."""
