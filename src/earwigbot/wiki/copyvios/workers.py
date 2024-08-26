# Copyright (C) 2009-2019 Ben Kurtovic <ben.kurtovic@gmail.com>
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

__all__ = ["globalize", "localize", "CopyvioWorkspace"]

import base64
import collections
import dataclasses
import functools
import gzip
import io
import logging
import math
import queue
import struct
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Container
from dataclasses import dataclass
from http.client import HTTPException
from typing import Any
from urllib.error import URLError

from earwigbot.exceptions import ParserExclusionError, ParserRedirectError
from earwigbot.wiki.copyvios.markov import (
    DEFAULT_DEGREE,
    MarkovChain,
    MarkovChainIntersection,
    MarkovChainUnion,
)
from earwigbot.wiki.copyvios.parsers import ParserArgs, SourceParser, get_parser
from earwigbot.wiki.copyvios.result import CopyvioCheckResult, CopyvioSource

INCLUDE_THRESHOLD = 0.15

_MAX_REDIRECTS = 3
_MAX_RAW_SIZE = 20 * 1024**2

_is_globalized = False
_global_queues: _CopyvioQueues | None = None
_global_workers: list[_CopyvioWorker] = []


def globalize(num_workers: int = 8) -> None:
    """
    Cause all copyvio checks to be done by one global set of workers.

    This is useful when checks are being done through a web interface where large
    numbers of simulatenous requests could be problematic. The global workers are
    spawned when the function is called, run continuously, and intelligently handle
    multiple checks.

    This function is not thread-safe and should only be called when no checks are being
    done. It has no effect if it has already been called.
    """
    global _is_globalized, _global_queues
    if _is_globalized:
        return

    _global_queues = _CopyvioQueues()
    for i in range(num_workers):
        worker = _CopyvioWorker(f"global-{i}", _global_queues)
        worker.start()
        _global_workers.append(worker)
    _is_globalized = True


def localize() -> None:
    """Return to using page-specific workers for copyvio checks.

    This disables changes made by :func:`globalize`, including stoping the global
    worker threads.

    This function is not thread-safe and should only be called when no checks are
    being done.
    """
    global _is_globalized, _global_queues, _global_workers
    if not _is_globalized:
        return

    assert _global_queues is not None
    for i in range(len(_global_workers)):
        _global_queues.unassigned.put((StopIteration, None))
    _global_queues = None
    _global_workers = []
    _is_globalized = False


@dataclass(frozen=True)
class OpenedURL:
    content: bytes
    parser_class: type[SourceParser]


SourceQueue = collections.deque[CopyvioSource]
UnassignedQueue = queue.Queue[
    tuple[str, SourceQueue] | tuple[type[StopIteration], None]
]


@dataclass(frozen=True)
class _CopyvioQueues:
    """Stores data necessary to maintain the various queues during a check."""

    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)
    sites: dict[str, SourceQueue] = dataclasses.field(default_factory=dict)
    unassigned: UnassignedQueue = dataclasses.field(default_factory=queue.Queue)


class _CopyvioWorker:
    """A multithreaded URL opener/parser instance."""

    def __init__(
        self, name: str, queues: _CopyvioQueues, until: float | None = None
    ) -> None:
        self._name = name
        self._queues = queues
        self._until = until

        self._site: str | None = None
        self._queue: SourceQueue | None = None
        self._search_config: dict[str, Any] | None = None
        self._opener = urllib.request.build_opener()
        self._logger = logging.getLogger("earwigbot.wiki.cvworker." + name)

    def _try_map_proxy_url(
        self,
        url: str,
        parsed: urllib.parse.ParseResult,
        extra_headers: dict[str, str],
        is_error: bool = False,
    ) -> tuple[str, bool]:
        if not self._search_config or "proxies" not in self._search_config:
            return url, False
        for proxy_info in self._search_config["proxies"]:
            if parsed.netloc != proxy_info["netloc"]:
                continue
            if "onerr" in proxy_info:
                if proxy_info["onerr"] and not is_error:
                    continue
                if not proxy_info["onerr"] and is_error:
                    continue
            path = parsed.path
            if "path" in proxy_info:
                if not parsed.path.startswith(proxy_info["path"]):
                    continue
                path = path[len(proxy_info["path"]) :]
            url = proxy_info["target"] + path
            if parsed.query:
                url += "?" + parsed.query
            if "auth" in proxy_info:
                auth_hash = base64.b64encode(proxy_info["auth"].encode()).decode()
                extra_headers["Authorization"] = f"Basic {auth_hash}"
            return url, True
        return url, False

    def _open_url_raw(
        self,
        url: str,
        timeout: float = 5,
        allow_content_types: Container[str] | None = None,
    ) -> OpenedURL | None:
        """Open a URL, without parsing it.

        None will be returned for URLs that cannot be read for whatever reason.
        """
        parsed = urllib.parse.urlparse(url)
        extra_headers: dict[str, str] = {}
        url, _ = self._try_map_proxy_url(url, parsed, extra_headers)
        request = urllib.request.Request(url, headers=extra_headers)
        try:
            response = self._opener.open(request, timeout=timeout)
        except (OSError, URLError, HTTPException, ValueError):
            url, remapped = self._try_map_proxy_url(
                url, parsed, extra_headers, is_error=True
            )
            if not remapped:
                self._logger.exception(f"Failed to fetch URL: {url}")
                return None
            self._logger.info(f"Failed to fetch URL, trying proxy remap: {url}")
            request = urllib.request.Request(url, headers=extra_headers)
            try:
                response = self._opener.open(request, timeout=timeout)
            except (OSError, URLError, HTTPException, ValueError):
                self._logger.exception(f"Failed to fetch URL after proxy remap: {url}")
                return None

        try:
            size = int(response.headers.get("Content-Length", 0))
        except ValueError:
            return None

        content_type = response.headers.get("Content-Type", "text/plain")
        content_type = content_type.split(";", 1)[0]
        parser_class = get_parser(content_type)
        if not parser_class and (
            not allow_content_types or content_type not in allow_content_types
        ):
            return None
        if not parser_class:
            parser_class = get_parser()
        if size > (15 if parser_class.TYPE == "PDF" else 2) * 1024**2:
            return None

        try:
            # Additional safety check for pages using Transfer-Encoding: chunked
            # where we can't read the Content-Length
            content = response.read(_MAX_RAW_SIZE + 1)
        except (OSError, URLError):
            return None
        if len(content) > _MAX_RAW_SIZE:
            return None

        if response.headers.get("Content-Encoding") == "gzip":
            stream = io.BytesIO(content)
            gzipper = gzip.GzipFile(fileobj=stream)
            try:
                content = gzipper.read()
            except (OSError, struct.error):
                return None

        if len(content) > _MAX_RAW_SIZE:
            return None
        return OpenedURL(content, parser_class)

    def _open_url(self, source: CopyvioSource, redirects: int = 0) -> str | None:
        """Open a URL and return its parsed content, or None.

        First, we will decompress the content if the headers contain "gzip" as its
        content encoding. Then, we will return the content stripped using an HTML
        parser if the headers indicate it is HTML, or return the content directly if it
        is plain text. If we don't understand the content type, we'll return None.

        If a URLError was raised while opening the URL or an IOError was raised while
        decompressing, None will be returned.
        """
        self._search_config = source.search_config
        if source.headers:
            self._opener.addheaders = source.headers

        result = self._open_url_raw(source.url, timeout=source.timeout)
        if result is None:
            return None

        args: ParserArgs = source.parser_args.copy() if source.parser_args else {}
        args["open_url"] = functools.partial(self._open_url_raw, timeout=source.timeout)
        parser = result.parser_class(result.content, source.url, args=args)
        try:
            return parser.parse()
        except ParserRedirectError as exc:
            if redirects >= _MAX_REDIRECTS:
                return None
            source.url = exc.url.decode("utf8")
            return self._open_url(source, redirects=redirects + 1)

    def _acquire_new_site(self) -> None:
        """Block for a new unassigned site queue."""
        if self._until:
            timeout = self._until - time.time()
            if timeout <= 0:
                raise queue.Empty()
        else:
            timeout = None

        self._logger.debug("Waiting for new site queue")
        site, q = self._queues.unassigned.get(timeout=timeout)
        if isinstance(site, type) and issubclass(site, StopIteration):
            raise StopIteration
        self._logger.debug(f"Acquired new site queue: {site}")
        self._site = site
        self._queue = q

    def _dequeue(self) -> CopyvioSource:
        """Remove a source from one of the queues."""
        if not self._site:
            self._acquire_new_site()
        assert self._site is not None
        assert self._queue is not None

        self._logger.debug(f"Fetching source URL from queue {self._site}")
        self._queues.lock.acquire()
        try:
            source = self._queue.popleft()
        except IndexError:
            self._logger.debug("Queue is empty")
            del self._queues.sites[self._site]
            self._site = None
            self._queue = None
            self._queues.lock.release()
            return self._dequeue()

        self._logger.debug(f"Got source URL: {source.url}")
        if source.skipped:
            self._logger.debug("Source has been skipped")
            self._queues.lock.release()
            return self._dequeue()

        source.start_work()
        self._queues.lock.release()
        return source

    def _handle_once(self) -> bool:
        """Handle a single source from one of the queues. Return if we should exit."""
        try:
            source = self._dequeue()
        except queue.Empty:
            self._logger.debug("Exiting: queue timed out")
            return False
        except StopIteration:
            self._logger.debug("Exiting: got stop signal")
            return False

        try:
            text = self._open_url(source)
        except ParserExclusionError:
            self._logger.debug("Source excluded by content parser")
            source.skipped = source.excluded = True
            source.finish_work()
        except Exception:
            self._logger.exception("Uncaught exception in worker")
            source.skip()
            source.finish_work()
        else:
            chain = MarkovChain(text, degree=source.workspace._degree) if text else None
            source.workspace.compare(source, chain)
        return True

    def _run(self) -> None:
        """Main entry point for the worker thread.

        We will keep fetching URLs from the queues and handling them until either we
        run out of time, or we get an exit signal that the queue is now empty.
        """
        while True:
            try:
                if not self._handle_once():
                    break
            except Exception:
                self._logger.exception("Uncaught exception in worker")
                time.sleep(5)  # Delay if we get stuck in a busy loop

    def start(self) -> None:
        """Start the copyvio worker in a new thread."""
        thread = threading.Thread(target=self._run, name="cvworker-" + self._name)
        thread.daemon = True
        thread.start()


class CopyvioWorkspace:
    """Manages a single copyvio check distributed across threads."""

    def __init__(
        self,
        article: MarkovChain,
        min_confidence: float,
        max_time: float,
        logger: logging.Logger,
        headers: list[tuple[str, str]],
        url_timeout: float = 5,
        num_workers: int = 8,
        short_circuit: bool = True,
        parser_args: ParserArgs | None = None,
        exclusion_callback: Callable[[str], bool] | None = None,
        config: dict[str, Any] | None = None,
        degree: int = DEFAULT_DEGREE,
    ) -> None:
        self.sources: list[CopyvioSource] = []
        self.finished = False
        self.possible_miss = False

        self._article = article
        self._logger = logger.getChild("copyvios")
        self._min_confidence = min_confidence
        self._start_time = time.time()
        self._until = (self._start_time + max_time) if max_time > 0 else None
        self._handled_urls: set[str] = set()
        self._finish_lock = threading.Lock()
        self._short_circuit = short_circuit
        self._source_args = {
            "workspace": self,
            "headers": headers,
            "timeout": url_timeout,
            "parser_args": parser_args,
            "search_config": config,
        }
        self._exclusion_callback = exclusion_callback
        self._degree = degree

        if _is_globalized:
            assert _global_queues is not None
            self._queues = _global_queues
        else:
            self._queues = _CopyvioQueues()
            self._num_workers = num_workers
            for i in range(num_workers):
                name = f"local-{id(self) % 10000:04}.{i}"
                _CopyvioWorker(name, self._queues, self._until).start()

    def _calculate_confidence(self, delta: MarkovChainIntersection) -> float:
        """Return the confidence of a violation as a float between 0 and 1."""

        def conf_with_article_and_delta(article: float, delta: float) -> float:
            """Calculate confidence using the article and delta chain sizes."""
            # This piecewise function exhibits exponential growth until it reaches the
            # default "suspect" confidence threshold, at which point it transitions to
            # polynomial growth with a limit of 1 as # (delta / article) approaches 1.
            # A graph can be viewed here: https://goo.gl/mKPhvr
            ratio = delta / article
            if ratio <= 0.52763:
                return -math.log(1 - ratio)
            else:
                return (-0.8939 * (ratio**2)) + (1.8948 * ratio) - 0.0009

        def conf_with_delta(delta: float) -> float:
            """Calculate confidence using just the delta chain size."""
            # This piecewise function was derived from experimental data using
            # reference points at (0, 0), (100, 0.5), (250, 0.75), (500, 0.9), and
            # (1000, 0.95), with a limit of 1 as delta approaches infinity. A graph can
            # be viewed here: https://goo.gl/lVl7or
            if delta <= 100:
                return delta / (delta + 100)
            elif delta <= 250:
                return (delta - 25) / (delta + 50)
            elif delta <= 500:
                return (10.5 * delta - 750) / (10 * delta)
            else:
                return (delta - 50) / delta

        d_size = float(delta.size)
        return abs(
            max(
                conf_with_article_and_delta(self._article.size, d_size),
                conf_with_delta(d_size),
            )
        )

    def _finish_early(self) -> None:
        """Finish handling links prematurely (if we've hit min_confidence)."""
        self._logger.debug("Confidence threshold met; skipping remaining sources")
        with self._queues.lock:
            for source in self.sources:
                source.skip()
            self.finished = True

    def enqueue(self, urls: list[str]) -> None:
        """Put a list of URLs into the various worker queues."""
        for url in urls:
            with self._queues.lock:
                if url in self._handled_urls:
                    continue
                self._handled_urls.add(url)

                source = CopyvioSource(url=url, **self._source_args)
                self.sources.append(source)

                if self._exclusion_callback and self._exclusion_callback(url):
                    self._logger.debug(f"enqueue(): exclude {url}")
                    source.excluded = True
                    source.skip()
                    continue
                if self._short_circuit and self.finished:
                    self._logger.debug(f"enqueue(): auto-skip {url}")
                    source.skip()
                    continue

                try:
                    import tldextract

                    key = tldextract.extract(url).registered_domain
                except ModuleNotFoundError:  # Fall back on very naive method
                    from urllib.parse import urlparse

                    key = ".".join(urlparse(url).netloc.split(".")[-2:])

                logmsg = f"enqueue(): %s {key} -> {url}"
                if key in self._queues.sites:
                    self._logger.debug(logmsg % "append")
                    self._queues.sites[key].append(source)
                else:
                    self._logger.debug(logmsg % "new")
                    q: SourceQueue = collections.deque()
                    q.append(source)
                    self._queues.sites[key] = q
                    self._queues.unassigned.put((key, q))

    def compare(self, source: CopyvioSource, source_chain: MarkovChain | None) -> None:
        """Compare a source to the article; call _finish_early if necessary."""
        if source_chain:
            delta = MarkovChainIntersection(self._article, source_chain)
            conf = self._calculate_confidence(delta)
        else:
            delta = None
            conf = 0.0
        self._logger.debug(f"compare(): {source.url} -> {conf}")
        with self._finish_lock:
            if source_chain:
                assert delta is not None
                source.update(conf, source_chain, delta)
            source.finish_work()
            if not self.finished and conf >= self._min_confidence:
                if self._short_circuit:
                    self._finish_early()
                else:
                    self.finished = True

    def wait(self) -> None:
        """Wait for the workers to finish handling the sources."""
        self._logger.debug(f"Waiting on {len(self.sources)} sources")
        for source in self.sources:
            source.join(self._until)
        with self._finish_lock:
            pass  # Wait for any remaining comparisons to be finished
        if not _is_globalized:
            for i in range(self._num_workers):
                self._queues.unassigned.put((StopIteration, None))

    def get_result(self, num_queries: int = 0) -> CopyvioCheckResult:
        """Return a CopyvioCheckResult containing the results of this check."""
        self.sources.sort(
            key=lambda s: (
                s.confidence,
                not s.excluded,
                not s.skipped,
                s.chains[0].size,
            ),
            reverse=True,
        )

        included_sources = [
            source for source in self.sources if source.confidence >= INCLUDE_THRESHOLD
        ]
        if included_sources:
            unified = MarkovChainUnion(source.chains[0] for source in included_sources)
            delta = MarkovChainIntersection(self._article, unified)
            unified_confidence = self._calculate_confidence(delta)
        else:
            unified_confidence = None

        return CopyvioCheckResult(
            self.finished,
            self.sources,
            num_queries,
            time.time() - self._start_time,
            self._article,
            self.possible_miss,
            included_sources,
            unified_confidence,
        )
