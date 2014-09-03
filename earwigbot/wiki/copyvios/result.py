# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2014 Ben Kurtovic <ben.kurtovic@gmail.com>
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
    """Represents a single suspected violation source (a URL)."""

    def __init__(self, workspace, url, key, headers=None, timeout=5):
        self.workspace = workspace
        self.url = url
        self.key = key
        self.headers = headers
        self.timeout = timeout
        self.confidence = 0.0
        self.chains = (EMPTY, EMPTY_INTERSECTION)

        self._event1 = Event()
        self._event2 = Event()
        self._event2.set()

    def touched(self):
        """Return whether one of start_work() and cancel() have been called."""
        return self._event1.is_set()

    def start_work(self):
        """Mark this source as being worked on right now."""
        self._event2.clear()
        self._event1.set()

    def finish_work(self, confidence, source_chain, delta_chain):
        """Complete the confidence information inside this source."""
        self.confidence = confidence
        self.chains = (source_chain, delta_chain)
        self._event2.set()

    def cancel(self):
        """Deactivate this source without filling in the relevant data."""
        self._event1.set()

    def join(self, until):
        """Block until this violation result is filled out."""
        for event in [self._event1, self._event2]:
            if until:
                timeout = until - time()
                if timeout <= 0:
                    return
                event.wait(timeout)


class CopyvioCheckResult(object):
    """
    **EarwigBot: Wiki Toolset: Copyvio Check Result**

    A class holding information about the results of a copyvio check.

    *Attributes:*

    - :py:attr:`violation`:     ``True`` if this is a violation, else ``False``
    - :py:attr:`confidence`:    a float between 0 and 1 indicating accuracy
    - :py:attr:`url`:           the URL of the violated page
    - :py:attr:`queries`:       the number of queries used to reach a result
    - :py:attr:`time`:          the amount of time the check took to complete
    - :py:attr:`article_chain`: the MarkovChain of the article text
    - :py:attr:`source_chain`:  the MarkovChain of the violated page text
    - :py:attr:`delta_chain`:   the MarkovChainIntersection comparing the two
    """

    def __init__(self, violation, confidence, url, queries, time, article,
                 chains):
        self.violation = violation
        self.confidence = confidence
        self.url = url
        self.queries = queries
        self.time = time
        self.article_chain = article
        self.source_chain = chains[0]
        self.delta_chain = chains[1]

    def __repr__(self):
        """Return the canonical string representation of the result."""
        res = "CopyvioCheckResult(violation={0!r}, confidence={1!r}, url={2!r}, queries={3!r})"
        return res.format(self.violation, self.confidence, self.url,
                          self.queries)

    def __str__(self):
        """Return a nice string representation of the result."""
        res = "<CopyvioCheckResult ({0} with {1} conf)>"
        return res.format(self.violation, self.confidence)

    def get_log_message(self, title):
        """Build a relevant log message for this copyvio check result."""
        log = u"{0} for [[{1}]] (confidence: {2}; URL: {3}; {4} queries; {5} seconds)"
        is_vio = "Violation detected" if self.violation else "No violation"
        return log.format(is_vio, title, self.confidence, self.url,
                          self.queries, self.time)
