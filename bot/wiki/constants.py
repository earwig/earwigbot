# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Toolset: Constants

This module defines some useful constants, such as default namespace IDs for
easy lookup and our user agent.

Import with `from wiki.constants import *`.
"""

import platform

# User agent when making API queries
USER_AGENT = "EarwigBot/0.1-dev (Python/{0}; https://github.com/earwig/earwigbot)".format(platform.python_version())

# Default namespace IDs
NS_MAIN = 0
NS_TALK = 1
NS_USER = 2
NS_USER_TALK = 3
NS_PROJECT = 4
NS_PROJECT_TALK = 5
NS_FILE = 6
NS_FILE_TALK = 7
NS_MEDIAWIKI = 8
NS_MEDIAWIKI_TALK = 9
NS_TEMPLATE = 10
NS_TEMPLATE_TALK = 11
NS_HELP = 12
NS_HELP_TALK = 13
NS_CATEGORY = 14
NS_CATEGORY_TALK = 15
NS_SPECIAL = -1
NS_MEDIA = -2
