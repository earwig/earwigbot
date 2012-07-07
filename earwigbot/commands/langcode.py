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

from earwigbot.commands import Command

class Langcode(Command):
    """Convert a language code into its name and a list of WMF sites in that
    language."""
    name = "langcode"
    commands = ["langcode", "lang", "language"]

    def process(self, data):
        if not data.args:
            self.reply(data, "please specify a language code.")
            return

        code = data.args[0]
        site = self.bot.wiki.get_site()
        matrix = site.api_query(action="sitematrix")["sitematrix"]
        del matrix["count"]
        del matrix["specials"]

        for site in matrix.itervalues():
            if site["code"] == code:
                name = site["name"].encode("utf8")
                localname = site["localname"].encode("utf8")
                if name != localname:
                    name += " ({0})".format(localname)
                sites = ", ".join([s["url"] for s in site["site"]])
                msg = "\x0302{0}\x0301 is {1} ({2})".format(code, name, sites)
                self.reply(data, msg)
                return

        self.reply(data, "language \x0302{0}\x0301 not found.".format(code))
