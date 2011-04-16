# -*- coding: utf-8  -*-

"""Convert a Wikipedia page name into a URL."""

import re

connection, data = None, None

def call(c, d):
    global connection, data
    connection, data = c, d

    msg = data.msg

    if re.search("(\[\[(.*?)\]\])|(\{\{(.*?)\}\})", msg):
        links = parse_line(msg)
        links = " , ".join(links)
        connection.reply(data.chan, data.nick, links)

    elif data.command == "!link":
        if not data.args:
            connection.reply(data.chan, data.nick, "what do you want me to link to?")
            return
        pagename = ' '.join(data.args)
        link = parse_link(pagename)
        connection.reply(data.chan, data.nick, link)

def parse_line(line):
    results = list()

    line = re.sub("\{\{\{(.*?)\}\}\}", "", line) # destroy {{{template parameters}}}

    links = re.findall("(\[\[(.*?)(\||\]\]))", line) # find all [[links]]
    if links:
        links = map(lambda x: x[1], links) # re.findall() returns a list of tuples, but we only want the 2nd item in each tuple
        results.extend(map(parse_link, links))

    templates = re.findall("(\{\{(.*?)(\||\}\}))", line) # find all {{templates}}
    if templates:
        templates = map(lambda x: x[1], templates)
        results.extend(map(parse_template, templates))

    return results

def parse_link(pagename):
    pagename = pagename.strip()
    link = "http://en.wikipedia.org/wiki/" + pagename
    link = link.replace(" ", "_")
    return link

def parse_template(pagename):
    pagename = "Template:%s" % pagename # TODO: implement an actual namespace check
    link = parse_link(pagename)
    return link
