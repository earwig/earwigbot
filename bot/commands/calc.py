# -*- coding: utf-8  -*-

import re
import urllib

from classes import BaseCommand

class Command(BaseCommand):
    """A somewhat advanced calculator: see http://futureboy.us/fsp/frink.fsp
    for details."""
    name = "calc"

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "what do you want me to calculate?")
            return

        query = ' '.join(data.args)
        query = self.cleanup(query)

        url = "http://futureboy.us/fsp/frink.fsp?fromVal={0}"
        url = url.format(urllib.quote(query))
        result = urllib.urlopen(url).read()

        r_result = re.compile(r'(?i)<A NAME=results>(.*?)</A>')
        r_tag = re.compile(r'<\S+.*?>')

        match = r_result.search(result)
        if not match:
            self.connection.reply(data, "Calculation error.")
            return

        result = match.group(1)
        result = r_tag.sub("", result) # strip span.warning tags
        result = result.replace("&gt;", ">")
        result = result.replace("(undefined symbol)", "(?) ")
        result = result.strip()

        if not result:
            result = '?'
        elif " in " in query: 
            result += " " + query.split(" in ", 1)[1]

        res = "%s = %s" % (query, result)
        self.connection.reply(data, res)

    def cleanup(self, query):
        fixes = [
            (' in ', ' -> '), 
            (' over ', ' / '), 
            (u'¬£', 'GBP '), 
            (u'‚Ç¨', 'EUR '), 
            ('\$', 'USD '), 
            (r'\bKB\b', 'kilobytes'), 
            (r'\bMB\b', 'megabytes'), 
            (r'\bGB\b', 'kilobytes'), 
            ('kbps', '(kilobits / second)'), 
            ('mbps', '(megabits / second)')
        ]

        for original, fix in fixes: 
            query = re.sub(original, fix, query)
        return query.strip()
