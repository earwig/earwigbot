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

from threading import Event
from time import time

from earwigbot.wiki.copyvios.markov import EMPTY, EMPTY_INTERSECTION

__all__ = ["CopyvioSource", "CopyvioCheckResult"]

class CopyvioSource(object):
    """
    **EarwigBot: Wiki Toolset: Copyvio Source**

    A class that represents a single possible source of a copyright violation,
    i.e., a URL.

    *Attributes:*

    - :py:attr:`url`:        the URL of the source
    - :py:attr:`confidence`: the confidence of a violation, between 0 and 1
    - :py:attr:`chains`:     a 2-tuple of the source chain and the delta chain
    - :py:attr:`skipped`:    whether this URL was skipped during the check
    - :py:attr:`excluded`:   whether this URL was in the exclusions list
    """

    def __init__(self, workspace, url, headers=None, timeout=5,
                 parser_args=None):
        self.workspace = workspace
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self.parser_args = parser_args

        self.confidence = 0.0
        self.chains = (EMPTY, EMPTY_INTERSECTION)
        self.skipped = False
        self.excluded = False

        self._event1 = Event()
        self._event2 = Event()
        self._event2.set()

    def __repr__(self):
        """Return the canonical string representation of the source."""
        res = ("CopyvioSource(url={0!r}, confidence={1!r}, skipped={2!r}, "
               "excluded={3!r})")
        return res.format(
            self.url, self.confidence, self.skipped, self.excluded)

    def __str__(self):
        """Return a nice string representation of the source."""
        if self.excluded:
            return "<CopyvioSource ({0}, excluded)>".format(self.url)
        if self.skipped:
            return "<CopyvioSource ({0}, skipped)>".format(self.url)
        res = "<CopyvioSource ({0} with {1} conf)>"
        return res.format(self.url, self.confidence)

    def start_work(self):
        """Mark this source as being worked on right now."""
        self._event2.clear()
        self._event1.set()

    def update(self, confidence, source_chain, delta_chain):
        """Fill out the confidence and chain information inside this source."""
        self.confidence = confidence
        self.chains = (source_chain, delta_chain)

    def finish_work(self):
        """Mark this source as finished."""
        self._event2.set()

    def skip(self):
        """Deactivate this source without filling in the relevant data."""
        if self._event1.is_set():
            return
        self.skipped = True
        self._event1.set()

    def join(self, until):
        """Block until this violation result is filled out."""
        for event in [self._event1, self._event2]:
            if until:
                timeout = until - time()
                if timeout <= 0:
                    return
                event.wait(timeout)
            else:
                event.wait()


class CopyvioCheckResult(object):
    """
    **EarwigBot: Wiki Toolset: Copyvio Check Result**

    A class holding information about the results of a copyvio check.

    *Attributes:*

    - :py:attr:`violation`:     ``True`` if this is a violation, else ``False``
    - :py:attr:`sources`:       a list of CopyvioSources, sorted by confidence
    - :py:attr:`best`:          the best matching CopyvioSource, or ``None``
    - :py:attr:`confidence`:    the best matching source's confidence, or 0
    - :py:attr:`url`:           the best matching source's URL, or ``None``
    - :py:attr:`queries`:       the number of queries used to reach a result
    - :py:attr:`time`:          the amount of time the check took to complete
    - :py:attr:`article_chain`: the MarkovChain of the article text
    - :py:attr:`possible_miss`: whether some URLs might have been missed
    """

    def __init__(self, violation, sources, queries, check_time, article_chain,
                 possible_miss):
        self.violation = violation
        self.sources = sources
        self.queries = queries
        self.time = check_time
        self.article_chain = article_chain
        self.possible_miss = possible_miss

    def __repr__(self):
        """Return the canonical string representation of the result."""
        res = "CopyvioCheckResult(violation={0!r}, sources={1!r}, queries={2!r}, time={3!r})"
        return res.format(self.violation, self.sources, self.queries,
                          self.time)

    def __str__(self):
        """Return a nice string representation of the result."""
        res = "<CopyvioCheckResult ({0} with best {1})>"
        return res.format(self.violation, self.best)

    @property
    def best(self):
        """The best known source, or None if no sources exist."""
        return self.sources[0] if self.sources else None

    @property
    def confidence(self):
        """The confidence of the best source, or 0 if no sources exist."""
        return self.best.confidence if self.best else 0.0

    @property
    def url(self):
        """The URL of the best source, or None if no sources exist."""
        return self.best.url if self.best else None

    def get_log_message(self, title):
        """Build a relevant log message for this copyvio check result."""
        if not self.sources:
            log = u"No violation for [[{0}]] (no sources; {1} queries; {2} seconds)"
            return log.format(title, self.queries, self.time)
        log = u"{0} for [[{1}]] (best: {2} ({3} confidence); {4} sources; {5} queries; {6} seconds)"
        is_vio = "Violation detected" if self.violation else "No violation"
        return log.format(is_vio, title, self.url, self.confidence,
                          len(self.sources), self.queries, self.time)
