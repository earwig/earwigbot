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
**EarwigBot: Wiki Toolset: Constants**

This module defines some useful constants:

- :py:const:`USER_AGENT`: our default User Agent when making API queries
- :py:const:`NS_*`:       default namespace IDs for easy lookup

Import directly with ``from earwigbot.wiki import constants`` or
``from earwigbot.wiki.constants import *``. These are also available from
:py:mod:`earwigbot.wiki` directly (e.g. ``earwigbot.wiki.USER_AGENT``).
"""

# Default User Agent when making API queries:
from earwigbot import __version__ as _v
from platform import python_version as _p
USER_AGENT = "EarwigBot/{0} (Python/{1}; https://github.com/earwig/earwigbot)"
USER_AGENT = USER_AGENT.format(_v, _p())
del _v, _p

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
NS_SPECIAL = -1
NS_MEDIA = -2
