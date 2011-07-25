# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Toolset: Exceptions

This module contains all exceptions used by the wiki.tools package.
"""

class WikiToolsetError(Exception):
    """Base exception class for errors in the Wiki Toolset."""

class ConfigError(WikiToolsetError):
    """An error occured when trying to do something involving our config
    file. Maybe it hasn't been loaded?"""

class SiteNotFoundError(WikiToolsetError):
    """A site matching the args given to get_site() could not be found in the
    config file."""

class UserNotFoundError(WikiToolsetError):
    """Attempting to get information about a user that does not exist."""
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return "User '{0}' does not exist.".format(self.name)
