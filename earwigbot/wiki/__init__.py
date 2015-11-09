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
**EarwigBot: Wiki Toolset**

This is a collection of classes and functions to read from and write to
Wikipedia and other wiki sites. No connection whatsoever to `python-wikitools
<http://code.google.com/p/python-wikitools/>`_ written by `Mr.Z-man
<http://en.wikipedia.org/wiki/User:Mr.Z-man>`_, other than a similar purpose.
We share no code.

Import the toolset directly with ``from earwigbot import wiki``. If using the
built-in integration with the rest of the bot, :py:class:`~earwigbot.bot.Bot`
objects contain a :py:attr:`~earwigbot.bot.Bot.wiki` attribute, which is a
:py:class:`~earwigbot.wiki.sitesdb.SitesDB` object tied to the :file:`sites.db`
file located in the same directory as :file:`config.yml`. That object has the
principal methods :py:meth:`~earwigbot.wiki.sitesdb.SitesDB.get_site`,
:py:meth:`~earwigbot.wiki.sitesdb.SitesDB.add_site`, and
:py:meth:`~earwigbot.wiki.sitesdb.SitesDB.remove_site` that should handle all
of your :py:class:`~earwigbot.wiki.site.Site` (and thus,
:py:class:`~earwigbot.wiki.page.Page`,
:py:class:`~earwigbot.wiki.category.Category`, and
:py:class:`~earwigbot.wiki.user.User`) needs.
"""

from earwigbot.wiki.category import *
from earwigbot.wiki.constants import *
from earwigbot.wiki.page import *
from earwigbot.wiki.site import *
from earwigbot.wiki.sitesdb import *
from earwigbot.wiki.user import *
