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
import urllib

from earwigbot.commands import Command

class Calc(Command):
    """A somewhat advanced calculator: see http://futureboy.us/fsp/frink.fsp
    for details."""
    name = "calc"

    def process(self, data):
        if not data.args:
            self.reply(data, "What do you want me to calculate?")
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
            self.reply(data, "Calculation error.")
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
        self.reply(data, res)

    def cleanup(self, query):
        fixes = [
            (' in ', ' -> '),
            (' over ', ' / '),
            (u'¬£', 'GBP '),
            (u'‚Ç¨', 'EUR '),
            ('\$', 'USD '),
            (r'\bKB\b', 'kilobytes'),
            (r'\bMB\b', 'megabytes'),
            (r'\bGB\b', 'gigabytes'),
            ('kbps', '(kilobits / second)'),
            ('mbps', '(megabits / second)')
        ]

        for original, fix in fixes:
            query = re.sub(original, fix, query)
        return query.strip()
