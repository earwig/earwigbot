# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Convert a language code into its name and a list of WMF sites in that
    language."""
    name = "langcode"

    def check(self, data):
        commands = ["langcode", "lang", "language"]
        return data.is_command and data.command in commands

    def process(self, data):
        if not data.args:
            self.reply(data, "please specify a language code.")
            return

        code = data.args[0]
        site = self.bot.wiki.get_site()
        matrix = site.api_query(action="sitematrix")["sitematrix"]
        del matrix["specials"]

        for site in matrix.itervalues():
            if site["code"] == code:
                name = site["name"]
                sites = ", ".join([s["url"] for s in site["site"]])
                msg = "\x0302{0}\x0302 is {1} ({2})".format(code, name, sites)
                self.reply(data, msg)
                return

        self.reply(data, "site \x0302{0}\x0301 not found.".format(code))
