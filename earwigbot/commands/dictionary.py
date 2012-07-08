# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

from earwigbot import exceptions
from earwigbot.commands import Command

class Dictionary(Command):
    """Define words and stuff."""
    name = "dictionary"
    commands = ["dict", "dictionary"]

    def process(self, data):
        if not data.args:
        	self.reply(data, "what do you want me to define?")
            return

        term = " ".join(data.args)
        lang = self.bot.wiki.get_site().lang
        try:
            definition = self.define(term, lang)
        except exceptions.APIError:
            msg = "cannot find a {0}-language Wiktionary."
            self.reply(data, msg.format(lang))
        else:
            self.reply(data, "{0}: {1}".format(term, definition))

    def define(self, term, lang):
        try:
            site = self.bot.wiki.get_site(project="wiktionary", lang=lang)
        except exceptions.SiteNotFoundError:
            site = self.bot.wiki.add_site(project="wiktionary", lang=lang)

        page = site.get_page(term)
        try:
            entry = page.get()
        except (exceptions.PageNotFoundError, exceptions.InvalidPageError):
            return "no definition found."

        return entry
