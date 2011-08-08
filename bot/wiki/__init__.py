# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Toolset

This is a collection of classes and functions to read from and write to
Wikipedia and other wiki sites. No connection whatsoever to python-wikitools
written by Mr.Z-man, other than a similar purpose. We share no code.

Import the toolset with `import wiki`.
"""

from wiki.constants import *
from wiki.exceptions import *
from wiki.functions import *

from wiki.category import Category
from wiki.page import Page
from wiki.site import Site
from wiki.user import User
