# -*- coding: utf-8  -*-

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
