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

__all__ = [
    "DEFAULT_DEGREE",
    "EMPTY",
    "EMPTY_INTERSECTION",
    "MarkovChain",
    "MarkovChainIntersection",
]

import re
from collections.abc import Iterable
from enum import Enum

DEFAULT_DEGREE = 5


class Sentinel(Enum):
    START = -1
    END = -2


RawChain = dict[tuple[str | Sentinel, ...], int]


class MarkovChain:
    """Implements a basic ngram Markov chain of words."""

    def __init__(self, text: str, degree: int = DEFAULT_DEGREE) -> None:
        self.text = text
        self.degree = degree  # 2 for bigrams, 3 for trigrams, etc.
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self) -> RawChain:
        """Build and return the Markov chain from the input text."""
        padding = self.degree - 1
        words = re.sub(r"[^\w\s-]", "", self.text.lower()).split()
        words = ([Sentinel.START] * padding) + words + ([Sentinel.END] * padding)
        chain: RawChain = {}

        for i in range(len(words) - self.degree + 1):
            phrase = tuple(words[i : i + self.degree])
            if phrase in chain:
                chain[phrase] += 1
            else:
                chain[phrase] = 1
        return chain

    def _get_size(self) -> int:
        """Return the size of the Markov chain: the total number of nodes."""
        return sum(self.chain.values())

    def __repr__(self) -> str:
        """Return the canonical string representation of the MarkovChain."""
        return f"MarkovChain(text={self.text!r})"

    def __str__(self) -> str:
        """Return a nice string representation of the MarkovChain."""
        return f"<MarkovChain of size {self.size}>"


class MarkovChainIntersection(MarkovChain):
    """Implements the intersection of two chains (i.e., their shared nodes)."""

    def __init__(self, mc1: MarkovChain, mc2: MarkovChain) -> None:
        self.mc1, self.mc2 = mc1, mc2
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self) -> RawChain:
        """Build and return the Markov chain from the input chains."""
        c1 = self.mc1.chain
        c2 = self.mc2.chain
        chain: RawChain = {}

        for phrase in c1:
            if phrase in c2:
                chain[phrase] = min(c1[phrase], c2[phrase])
        return chain

    def __repr__(self) -> str:
        """Return the canonical string representation of the intersection."""
        return f"MarkovChainIntersection(mc1={self.mc1!r}, mc2={self.mc2!r})"

    def __str__(self) -> str:
        """Return a nice string representation of the intersection."""
        return (
            f"<MarkovChainIntersection of size {self.size} ({self.mc1} ^ {self.mc2})>"
        )


class MarkovChainUnion(MarkovChain):
    """Implemented the union of multiple chains."""

    def __init__(self, chains: Iterable[MarkovChain]) -> None:
        self.chains = list(chains)
        self.chain = self._build()
        self.size = self._get_size()

    def _build(self) -> RawChain:
        """Build and return the Markov chain from the input chains."""
        union: RawChain = {}
        for chain in self.chains:
            for phrase, count in chain.chain.items():
                if phrase in union:
                    union[phrase] += count
                else:
                    union[phrase] = count
        return union

    def __repr__(self) -> str:
        """Return the canonical string representation of the union."""
        return f"MarkovChainUnion(chains={self.chains!r})"

    def __str__(self) -> str:
        """Return a nice string representation of the union."""
        chains = " | ".join(str(chain) for chain in self.chains)
        return f"<MarkovChainUnion of size {self.size} ({chains})>"


EMPTY = MarkovChain("")
EMPTY_INTERSECTION = MarkovChainIntersection(EMPTY, EMPTY)
