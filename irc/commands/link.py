# -*- coding: utf-8  -*-

# Convert a Wikipedia page name into a URL.

import re

from irc.classes import BaseCommand

class Link(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Convert a Wikipedia page name into a URL."

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
        results = list()

        line = re.sub("\{\{\{(.*?)\}\}\}", "", line) # destroy {{{template parameters}}}

        links = re.findall("(\[\[(.*?)(\||\]\]))", line) # find all [[links]]
        if links:
            links = map(lambda x: x[1], links) # re.findall() returns a list of tuples, but we only want the 2nd item in each tuple
            results.extend(map(self.parse_link, links))

        templates = re.findall("(\{\{(.*?)(\||\}\}))", line) # find all {{templates}}
        if templates:
            templates = map(lambda x: x[1], templates)
            results.extend(map(self.parse_template, templates))

        return results

    def parse_link(self, pagename):
        pagename = pagename.strip()
        link = "http://enwp.org/" + pagename
        link = link.replace(" ", "_")
        return link

    def parse_template(self, pagename):
        pagename = "Template:%s" % pagename # TODO: implement an actual namespace check
        link = self.parse_link(pagename)
        return link
