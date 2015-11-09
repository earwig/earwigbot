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

import re

from earwigbot.commands import Command

class Link(Command):
    """Convert a Wikipedia page name into a URL."""
    name = "link"

    def setup(self):
        self.last = {}

    def check(self, data):
        if re.search("(\[\[(.*?)\]\])|(\{\{(.*?)\}\})", data.msg):
            self.last[data.chan] = data.msg  # Store most recent link
        return data.is_command and data.command == self.name

    def process(self, data):
        self.site = self.bot.wiki.get_site()

        if re.search("(\[\[(.*?)\]\])|(\{\{(.*?)\}\})", data.msg):
            links = u" , ".join(self.parse_line(data.msg))
            self.reply(data, links.encode("utf8"))

        elif data.command == "link":
            if not data.args:
                if data.chan in self.last:
                    links = u" , ".join(self.parse_line(self.last[data.chan]))
                    self.reply(data, links.encode("utf8"))
                else:
                    self.reply(data, "What do you want me to link to?")
                return
            pagename = " ".join(data.args)
            link = self.site.get_page(pagename).url.encode("utf8")
            self.reply(data, link)

    def parse_line(self, line):
        """Return a list of links within a line of text."""
        results = []

        # Destroy {{{template parameters}}}:
        line = re.sub("\{\{\{(.*?)\}\}\}", "", line)

        # Find all [[links]]:
        links = re.findall("(\[\[(.*?)(\||\]\]))", line)
        if links:
            # re.findall() returns a list of tuples, but we only want the 2nd
            # item in each tuple:
            results = [self.site.get_page(name[1]).url for name in links]

        # Find all {{templates}}
        templates = re.findall("(\{\{(.*?)(\||\}\}))", line)
        if templates:
            p_tmpl = lambda name: self.site.get_page("Template:" + name).url
            templates = [p_tmpl(i[1]) for i in templates]
            results += templates

        return results
