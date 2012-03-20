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

from collections import defaultdict
from re import sub, UNICODE

class MarkovChain(object):
    START = -1
    END = -2

    def __init__(self, text):
        self.text = text
        self.chain = defaultdict(lambda: defaultdict(lambda: 0))
        words = sub("[^\w\s-]", "", text.lower(), flags=UNICODE).split()
        prev = self.START
        for word in words:
            self.chain[prev][word] += 1
            prev = word
        try:  # This won't work if the source text is completely blank
            self.chain[word][self.END] += 1
        except KeyError:
            pass

    def size(self):
        count = 0
        for node in self.chain.itervalues():
            for hits in node.itervalues():
                count += hits
        return count


class MarkovChainIntersection(MarkovChain):
    def __init__(self, mc1, mc2):
        self.chain = defaultdict(lambda: defaultdict(lambda: 0))
        c1 = mc1.chain
        c2 = mc2.chain

        for word, nodes1 in c1.iteritems():
            if word in c2:
                nodes2 = c2[word]
                for node, count1 in nodes1.iteritems():
                    if node in nodes2:
                        count2 = nodes2[node]
                        self.chain[word][node] = min(count1, count2)
