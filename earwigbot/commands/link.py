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

import re
from urllib import quote

from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Convert a Wikipedia page name into a URL."""
    name = "link"

    def check(self, data):
        # if ((data.is_command and data.command == "link") or
        # (("[[" in data.msg and "]]" in data.msg) or
        # ("{{" in data.msg and "}}" in data.msg))):
        if data.is_command and data.command == "link":
            return True
        return False

    def process(self, data):
        msg = data.msg

        if re.search("(\[\[(.*?)\]\])|(\{\{(.*?)\}\})", msg):
            links = self.parse_line(msg)
            links = " , ".join(links)
            self.connection.reply(data, links)

        elif data.command == "link":
            if not data.args:
                self.connection.reply(data, "what do you want me to link to?")
                return
            pagename = ' '.join(data.args)
            link = self.parse_link(pagename)
            self.connection.reply(data, link)

    def parse_line(self, line):
        results = []

        # Destroy {{{template parameters}}}:
        line = re.sub("\{\{\{(.*?)\}\}\}", "", line)

        # Find all [[links]]:
        links = re.findall("(\[\[(.*?)(\||\]\]))", line)
        if links:
            # re.findall() returns a list of tuples, but we only want the 2nd
            # item in each tuple:
            links = [i[1] for i in links]
            results = map(self.parse_link, links)

        # Find all {{templates}}
        templates = re.findall("(\{\{(.*?)(\||\}\}))", line)
        if templates:
            templates = [i[1] for i in templates]
            results.extend(map(self.parse_template, templates))

        return results

    def parse_link(self, pagename):
        link = quote(pagename.replace(" ", "_"), safe="/:")
        return "".join(("http://enwp.org/", link))

    def parse_template(self, pagename):
        pagename = "".join(("Template:", pagename))
        return self.parse_link(pagename)
