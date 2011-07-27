# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Toolset

This is a collection of classes and functions to read from and write to
Wikipedia and other wiki sites. No connection whatsoever to python-wikitools
written by Mr.Z-man, other than a similar purpose. We share no code.

Import the toolset with `from wiki import tools`.
"""

from wiki.tools.constants import *
from wiki.tools.exceptions import *
from wiki.tools.functions import *

from wiki.tools.category import Category
from wiki.tools.page import Page
from wiki.tools.site import Site
from wiki.tools.user import User
