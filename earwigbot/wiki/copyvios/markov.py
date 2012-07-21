# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

__all__ = ["MarkovChain", "MarkovChainIntersection"]

class MarkovChain(object):
    """Implements a basic ngram Markov chain of words."""
    START = -1
    END = -2
    degree = 3  # 2 for bigrams, 3 for trigrams, etc.

    def __init__(self, text):
        self.text = text
        self.chain = defaultdict(lambda: defaultdict(lambda: 0))
        words = sub("[^\w\s-]", "", text.lower(), flags=UNICODE).split()

        padding = self.degree - 1
        words = ([self.START] * padding) + words + ([self.END] * padding)
        for i in range(len(words) - self.degree + 1):
            last = i + self.degree - 1
            self.chain[tuple(words[i:last])][words[last]] += 1

    def __repr__(self):
        """Return the canonical string representation of the MarkovChain."""
        return "MarkovChain(text={0!r})".format(self.text)

    def __str__(self):
        """Return a nice string representation of the MarkovChain."""
        return "<MarkovChain of size {0}>".format(self.size())

    def size(self):
        """Return the size of the Markov chain: the total number of nodes."""
        count = 0
        for node in self.chain.itervalues():
            for hits in node.itervalues():
                count += hits
        return count


class MarkovChainIntersection(MarkovChain):
    """Implements the intersection of two chains (i.e., their shared nodes)."""

    def __init__(self, mc1, mc2):
        self.chain = defaultdict(lambda: defaultdict(lambda: 0))
        self.mc1, self.mc2 = mc1, mc2
        c1 = mc1.chain
        c2 = mc2.chain

        for word, nodes1 in c1.iteritems():
            if word in c2:
                nodes2 = c2[word]
                for node, count1 in nodes1.iteritems():
                    if node in nodes2:
                        count2 = nodes2[node]
                        self.chain[word][node] = min(count1, count2)

    def __repr__(self):
        """Return the canonical string representation of the intersection."""
        res = "MarkovChainIntersection(mc1={0!r}, mc2={1!r})"
        return res.format(self.mc1, self.mc2)

    def __str__(self):
        """Return a nice string representation of the intersection."""
        res = "<MarkovChainIntersection of size {0} ({1} ^ {2})>"
        return res.format(self.size(), self.mc1, self.mc2)
