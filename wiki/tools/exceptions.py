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

class UserNotFoundError(WikiToolsetError):
    """Attempting to get information about a user that does not exist."""
