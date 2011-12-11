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
EarwigBot's Wiki Toolset

This is a collection of classes and functions to read from and write to
Wikipedia and other wiki sites. No connection whatsoever to python-wikitools
written by Mr.Z-man, other than a similar purpose. We share no code.

Import the toolset with `from earwigbot import wiki`.
"""

import logging as _log
logger = _log.getLogger("earwigbot.wiki")
logger.addHandler(_log.NullHandler())

from earwigbot.wiki.constants import *
from earwigbot.wiki.exceptions import *
from earwigbot.wiki.functions import *

from earwigbot.wiki.category import Category
from earwigbot.wiki.page import Page
from earwigbot.wiki.site import Site
from earwigbot.wiki.user import User
