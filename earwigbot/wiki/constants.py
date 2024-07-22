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
**EarwigBot: Wiki Toolset: Constants**

This module defines some useful constants:

- :py:const:`USER_AGENT`: our default User Agent when making API queries
- :py:const:`NS_*`:       default namespace IDs for easy lookup

Import directly with ``from earwigbot.wiki import constants`` or
``from earwigbot.wiki.constants import *``. These are also available from
:py:mod:`earwigbot.wiki` directly (e.g. ``earwigbot.wiki.USER_AGENT``).
"""

__all__ = [
    "NS_CATEGORY_TALK",
    "NS_CATEGORY",
    "NS_DRAFT_TALK",
    "NS_DRAFT",
    "NS_FILE_TALK",
    "NS_FILE",
    "NS_HELP_TALK",
    "NS_HELP",
    "NS_MAIN",
    "NS_MEDIA",
    "NS_MEDIAWIKI_TALK",
    "NS_MEDIAWIKI",
    "NS_MODULE_TALK",
    "NS_MODULE",
    "NS_PORTAL_TALK",
    "NS_PORTAL",
    "NS_PROJECT_TALK",
    "NS_PROJECT",
    "NS_SPECIAL",
    "NS_TALK",
    "NS_TEMPLATE_TALK",
    "NS_TEMPLATE",
    "NS_USER_TALK",
    "NS_USER",
    "USER_AGENT",
]

import platform
from enum import Enum

import earwigbot

# Default User Agent when making API queries:
USER_AGENT = (
    f"EarwigBot/{earwigbot.__version__} "
    f"(Python/{platform.python_version()}; https://github.com/earwig/earwigbot)"
)


class Service(Enum):
    API = 1
    SQL = 2


# Default namespace IDs:
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

NS_PORTAL = 100
NS_PORTAL_TALK = 101
NS_DRAFT = 118
NS_DRAFT_TALK = 119
NS_MODULE = 828
NS_MODULE_TALK = 829

NS_SPECIAL = -1
NS_MEDIA = -2
