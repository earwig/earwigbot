# -*- coding: utf-8  -*-

import re
from urllib import quote

from classes import BaseCommand

class Command(BaseCommand):
    """Convert a Wikipedia page name into a URL."""
    name = "link"

    def check(self, data):
        if ((data.is_command and data.command == "link") or
        (("[[" in data.msg and "]]" in data.msg) or
        ("{{" in data.msg and "}}" in data.msg))):
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
