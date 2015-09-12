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

from earwigbot.commands import Command

class Watchers(Command):
    """Get the number of users watching a given page."""
    name = "watchers"

    def process(self, data):
        if not data.args:
            msg = "Which page do you want me to count the watchers of?"
            self.reply(data, msg)
            return

        site = self.bot.wiki.get_site()
        query = site.api_query(action="query", prop="info", inprop="watchers",
                               titles=" ".join(data.args))
        page = query["query"]["pages"].values()[0]
        title = page["title"].encode("utf8")

        if "invalid" in page:
            msg = "\x0302{0}\x0F is an invalid page title."
            self.reply(data, msg.format(title))
            return

        if "watchers" in page:
            watchers = page["watchers"]
        else:
            watchers = "<30"
        plural = "" if watchers == 1 else "s"
        msg = "\x0302{0}\x0F has \x02{1}\x0F watcher{2}."
        self.reply(data, msg.format(title, watchers, plural))
