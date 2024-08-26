# Copyright (C) 2009-2024 Ben Kurtovic <ben.kurtovic@gmail.com>
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

__all__ = ["EMPTY", "EMPTY_INTERSECTION", "MarkovChain", "MarkovChainIntersection"]


class MarkovChain:
    """Implements a basic ngram Markov chain of words."""

    START = -1
    END = -2

    def __init__(self, text, degree=5):
        self.text = text
        self.degree = degree  # 2 for bigrams, 3 for trigrams, etc.
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self):
        """Build and return the Markov chain from the input text."""
        padding = self.degree - 1
        words = re.sub(r"[^\w\s-]", "", self.text.lower(), flags=re.UNICODE).split()
        words = ([self.START] * padding) + words + ([self.END] * padding)
        chain = {}

        for i in range(len(words) - self.degree + 1):
            phrase = tuple(words[i : i + self.degree])
            if phrase in chain:
                chain[phrase] += 1
            else:
                chain[phrase] = 1
        return chain

    def _get_size(self):
        """Return the size of the Markov chain: the total number of nodes."""
        return sum(self.chain.values())

    def __repr__(self):
        """Return the canonical string representation of the MarkovChain."""
        return f"MarkovChain(text={self.text!r})"

    def __str__(self):
        """Return a nice string representation of the MarkovChain."""
        return f"<MarkovChain of size {self.size}>"


class MarkovChainIntersection(MarkovChain):
    """Implements the intersection of two chains (i.e., their shared nodes)."""

    def __init__(self, mc1, mc2):
        self.mc1, self.mc2 = mc1, mc2
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self):
        """Build and return the Markov chain from the input chains."""
        c1 = self.mc1.chain
        c2 = self.mc2.chain
        chain = {}

        for phrase in c1:
            if phrase in c2:
                chain[phrase] = min(c1[phrase], c2[phrase])
        return chain

    def __repr__(self):
        """Return the canonical string representation of the intersection."""
        res = "MarkovChainIntersection(mc1={0!r}, mc2={1!r})"
        return res.format(self.mc1, self.mc2)

    def __str__(self):
        """Return a nice string representation of the intersection."""
        res = "<MarkovChainIntersection of size {0} ({1} ^ {2})>"
        return res.format(self.size, self.mc1, self.mc2)


class MarkovChainUnion(MarkovChain):
    """Implemented the union of multiple chains."""

    def __init__(self, chains):
        self.chains = list(chains)
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self):
        """Build and return the Markov chain from the input chains."""
        union = {}
        for chain in self.chains:
            for phrase, count in chain.chain.iteritems():
                if phrase in union:
                    union[phrase] += count
                else:
                    union[phrase] = count
        return union

    def __repr__(self):
        """Return the canonical string representation of the union."""
        res = "MarkovChainUnion(chains={!r})"
        return res.format(self.chains)

    def __str__(self):
        """Return a nice string representation of the union."""
        res = "<MarkovChainUnion of size {} ({})>"
        return res.format(self.size, "| ".join(str(chain) for chain in self.chains))


EMPTY = MarkovChain("")
EMPTY_INTERSECTION = MarkovChainIntersection(EMPTY, EMPTY)
