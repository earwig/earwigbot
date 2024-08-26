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

from __future__ import annotations

__all__ = ["CopyvioSource", "CopyvioCheckResult"]

import time
import typing
import urllib.parse
from threading import Event
from typing import Any

from earwigbot.wiki.copyvios.markov import (
    EMPTY,
    EMPTY_INTERSECTION,
    MarkovChain,
    MarkovChainIntersection,
)

if typing.TYPE_CHECKING:
    from earwigbot.wiki.copyvios.parsers import ParserArgs
    from earwigbot.wiki.copyvios.workers import CopyvioWorkspace


class CopyvioSource:
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

    def __init__(
        self,
        workspace: CopyvioWorkspace,
        url: str,
        headers: list[tuple[str, str]] | None = None,
        timeout: float = 5,
        parser_args: ParserArgs | None = None,
        search_config: dict[str, Any] | None = None,
    ) -> None:
        self.workspace = workspace
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self.parser_args = parser_args
        self.search_config = search_config

        self.confidence = 0.0
        self.chains = (EMPTY, EMPTY_INTERSECTION)
        self.skipped = False
        self.excluded = False

        self._event1 = Event()
        self._event2 = Event()
        self._event2.set()

    def __repr__(self) -> str:
        """Return the canonical string representation of the source."""
        return (
            f"CopyvioSource(url={self.url!r}, confidence={self.confidence!r}, "
            f"skipped={self.skipped!r}, excluded={self.excluded!r})"
        )

    def __str__(self) -> str:
        """Return a nice string representation of the source."""
        if self.excluded:
            return f"<CopyvioSource ({self.url}, excluded)>"
        if self.skipped:
            return f"<CopyvioSource ({self.url}, skipped)>"
        return f"<CopyvioSource ({self.url} with {self.confidence} conf)>"

    @property
    def domain(self) -> str | None:
        """The source URL's domain name, or None."""
        return urllib.parse.urlparse(self.url).netloc or None

    def start_work(self) -> None:
        """Mark this source as being worked on right now."""
        self._event2.clear()
        self._event1.set()

    def update(
        self,
        confidence: float,
        source_chain: MarkovChain,
        delta_chain: MarkovChainIntersection,
    ) -> None:
        """Fill out the confidence and chain information inside this source."""
        self.confidence = confidence
        self.chains = (source_chain, delta_chain)

    def finish_work(self) -> None:
        """Mark this source as finished."""
        self._event2.set()

    def skip(self) -> None:
        """Deactivate this source without filling in the relevant data."""
        if self._event1.is_set():
            return
        self.skipped = True
        self._event1.set()

    def join(self, until: float | None = None) -> None:
        """Block until this violation result is filled out."""
        for event in [self._event1, self._event2]:
            if until is not None:
                timeout = until - time.time()
                if timeout <= 0:
                    return
                event.wait(timeout)
            else:
                event.wait()


class CopyvioCheckResult:
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

    def __init__(
        self,
        violation: bool,
        sources: list[CopyvioSource],
        queries: int,
        check_time: float,
        article_chain: MarkovChain,
        possible_miss: bool,
        included_sources: list[CopyvioSource] | None = None,
        unified_confidence: float | None = None,
    ):
        self.violation = violation
        self.sources = sources
        self.queries = queries
        self.time = check_time
        self.article_chain = article_chain
        self.possible_miss = possible_miss
        self.included_sources = included_sources if included_sources else []
        self.unified_confidence = unified_confidence

    def __repr__(self) -> str:
        """Return the canonical string representation of the result."""
        return (
            f"CopyvioCheckResult(violation={self.violation!r}, "
            f"sources={self.sources!r}, queries={self.queries!r}, time={self.time!r})"
        )

    def __str__(self) -> str:
        """Return a nice string representation of the result."""
        return f"<CopyvioCheckResult ({self.violation} with best {self.best})>"

    @property
    def best(self) -> CopyvioSource | None:
        """The best known source, or None if no sources exist."""
        return self.sources[0] if self.sources else None

    @property
    def confidence(self) -> float:
        """The confidence of the best source, or 0 if no sources exist."""
        if self.unified_confidence is not None:
            return self.unified_confidence
        if self.best is not None:
            return self.best.confidence
        return 0.0

    @property
    def url(self) -> str | None:
        """The URL of the best source, or None if no sources exist."""
        return self.best.url if self.best else None

    def get_log_message(self, title: str) -> str:
        """Build a relevant log message for this copyvio check result."""
        if not self.sources:
            return (
                f"No violation for [[{title}]] (no sources; {self.queries} queries; "
                f"{self.time} seconds)"
            )

        is_vio = "Violation detected" if self.violation else "No violation"
        return (
            f"{is_vio} for [[{title}]] (best: {self.url} ({self.confidence} "
            f"confidence); {len(self.sources)} sources; {self.queries} queries; "
            f"{self.time} seconds)"
        )
