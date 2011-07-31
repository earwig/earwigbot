# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Toolset: Exceptions

This module contains all exceptions used by the wiki.tools package.
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

class PermissionsError(WikiToolsetError):
    """We tried to do something we don't have permission to, like a non-admin
    trying to delete a page, or trying to edit a page when no login information
    was provided."""

class NamespaceNotFoundError(WikiToolsetError):
    """A requested namespace name or namespace ID does not exist."""

class UserNotFoundError(WikiToolsetError):
    """Attempting to get information about a user that does not exist."""
