# -*- coding: utf-8  -*-
#
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

from collections import deque
from gzip import GzipFile
from httplib import HTTPException
from logging import getLogger
from math import log
from Queue import Empty, Queue
from socket import error as socket_error
from StringIO import StringIO
from struct import error as struct_error
from threading import Lock, Thread
from time import time
from urllib2 import build_opener, URLError

from earwigbot import importer
from earwigbot.exceptions import ParserExclusionError
from earwigbot.wiki.copyvios.markov import MarkovChain, MarkovChainIntersection
from earwigbot.wiki.copyvios.parsers import get_parser
from earwigbot.wiki.copyvios.result import CopyvioCheckResult, CopyvioSource

tldextract = importer.new("tldextract")

__all__ = ["globalize", "localize", "CopyvioWorkspace"]

_is_globalized = False
_global_queues = None
_global_workers = []

def globalize(num_workers=8):
    """Cause all copyvio checks to be done by one global set of workers.

    This is useful when checks are being done through a web interface where
    large numbers of simulatenous requests could be problematic. The global
    workers are spawned when the function is called, run continuously, and
    intelligently handle multiple checks.

    This function is not thread-safe and should only be called when no checks
    are being done. It has no effect if it has already been called.
    """
    global _is_globalized, _global_queues
    if _is_globalized:
        return

    _global_queues = _CopyvioQueues()
    for i in xrange(num_workers):
        worker = _CopyvioWorker("global-{0}".format(i), _global_queues)
        worker.start()
        _global_workers.append(worker)
    _is_globalized = True

def localize():
    """Return to using page-specific workers for copyvio checks.

    This disables changes made by :func:`globalize`, including stoping the
    global worker threads.

    This function is not thread-safe and should only be called when no checks
    are being done.
    """
    global _is_globalized, _global_queues, _global_workers
    if not _is_globalized:
        return

    for i in xrange(len(_global_workers)):
        _global_queues.unassigned.put((StopIteration, None))
    _global_queues = None
    _global_workers = []
    _is_globalized = False


class _CopyvioQueues(object):
    """Stores data necessary to maintain the various queues during a check."""

    def __init__(self):
        self.lock = Lock()
        self.sites = {}
        self.unassigned = Queue()


class _CopyvioWorker(object):
    """A multithreaded URL opener/parser instance."""

    def __init__(self, name, queues, until=None):
        self._name = name
        self._queues = queues
        self._until = until

        self._site = None
        self._queue = None
        self._opener = build_opener()
        self._logger = getLogger("earwigbot.wiki.cvworker." + name)

    def _open_url(self, source):
        """Open a URL and return its parsed content, or None.

        First, we will decompress the content if the headers contain "gzip" as
        its content encoding. Then, we will return the content stripped using
        an HTML parser if the headers indicate it is HTML, or return the
        content directly if it is plain text. If we don't understand the
        content type, we'll return None.

        If a URLError was raised while opening the URL or an IOError was raised
        while decompressing, None will be returned.
        """
        if source.headers:
            self._opener.addheaders = source.headers
        url = source.url.encode("utf8")
        try:
            response = self._opener.open(url, timeout=source.timeout)
        except (URLError, HTTPException, socket_error, ValueError):
            return None

        try:
            size = int(response.headers.get("Content-Length", 0))
        except ValueError:
            return None

        content_type = response.headers.get("Content-Type", "text/plain")
        handler = get_parser(content_type)
        if not handler:
            return None
        if size > (15 if handler.TYPE == "PDF" else 2) * 1024 ** 2:
            return None

        try:
            content = response.read()
        except (URLError, socket_error):
            return None

        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(content)
            gzipper = GzipFile(fileobj=stream)
            try:
                content = gzipper.read()
            except (IOError, struct_error):
                return None

        return handler(content, source.parser_args).parse()

    def _acquire_new_site(self):
        """Block for a new unassigned site queue."""
        if self._until:
            timeout = self._until - time()
            if timeout <= 0:
                raise Empty
        else:
            timeout = None

        self._logger.debug("Waiting for new site queue")
        site, queue = self._queues.unassigned.get(timeout=timeout)
        if site is StopIteration:
            raise StopIteration
        self._logger.debug(u"Acquired new site queue: {0}".format(site))
        self._site = site
        self._queue = queue

    def _dequeue(self):
        """Remove a source from one of the queues."""
        if not self._site:
            self._acquire_new_site()

        logmsg = u"Fetching source URL from queue {0}"
        self._logger.debug(logmsg.format(self._site))
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

        self._logger.debug(u"Got source URL: {0}".format(source.url))
        if source.skipped:
            self._logger.debug("Source has been skipped")
            self._queues.lock.release()
            return self._dequeue()

        source.start_work()
        self._queues.lock.release()
        return source

    def _handle_once(self):
        """Handle a single source from one of the queues."""
        try:
            source = self._dequeue()
        except Empty:
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
        else:
            chain = MarkovChain(text) if text else None
            source.workspace.compare(source, chain)
        return True

    def _run(self):
        """Main entry point for the worker thread.

        We will keep fetching URLs from the queues and handling them until
        either we run out of time, or we get an exit signal that the queue is
        now empty.
        """
        while True:
            if not self._handle_once():
                break

    def start(self):
        """Start the copyvio worker in a new thread."""
        thread = Thread(target=self._run, name="cvworker-" + self._name)
        thread.daemon = True
        thread.start()


class CopyvioWorkspace(object):
    """Manages a single copyvio check distributed across threads."""

    def __init__(self, article, min_confidence, max_time, logger, headers,
                 url_timeout=5, num_workers=8, short_circuit=True,
                 parser_args=None):
        self.sources = []
        self.finished = False
        self.possible_miss = False

        self._article = article
        self._logger = logger.getChild("copyvios")
        self._min_confidence = min_confidence
        self._start_time = time()
        self._until = (self._start_time + max_time) if max_time > 0 else None
        self._handled_urls = set()
        self._finish_lock = Lock()
        self._short_circuit = short_circuit
        self._source_args = {
            "workspace": self, "headers": headers, "timeout": url_timeout,
            "parser_args": parser_args}

        if _is_globalized:
            self._queues = _global_queues
        else:
            self._queues = _CopyvioQueues()
            self._num_workers = num_workers
            for i in xrange(num_workers):
                name = "local-{0:04}.{1}".format(id(self) % 10000, i)
                _CopyvioWorker(name, self._queues, self._until).start()

    def _calculate_confidence(self, delta):
        """Return the confidence of a violation as a float between 0 and 1."""
        def conf_with_article_and_delta(article, delta):
            """Calculate confidence using the article and delta chain sizes."""
            # This piecewise function exhibits exponential growth until it
            # reaches the default "suspect" confidence threshold, at which
            # point it transitions to polynomial growth with a limit of 1 as
            # (delta / article) approaches 1.
            # A graph can be viewed here: http://goo.gl/mKPhvr
            ratio = delta / article
            if ratio <= 0.52763:
                return -log(1 - ratio)
            else:
                return (-0.8939 * (ratio ** 2)) + (1.8948 * ratio) - 0.0009

        def conf_with_delta(delta):
            """Calculate confidence using just the delta chain size."""
            # This piecewise function was derived from experimental data using
            # reference points at (0, 0), (100, 0.5), (250, 0.75), (500, 0.9),
            # and (1000, 0.95), with a limit of 1 as delta approaches infinity.
            # A graph can be viewed here: http://goo.gl/lVl7or
            if delta <= 100:
                return delta / (delta + 100)
            elif delta <= 250:
                return (delta - 25) / (delta + 50)
            elif delta <= 500:
                return (10.5 * delta - 750) / (10 * delta)
            else:
                return (delta - 50) / delta

        d_size = float(delta.size)
        return abs(max(conf_with_article_and_delta(self._article.size, d_size),
                       conf_with_delta(d_size)))

    def _finish_early(self):
        """Finish handling links prematurely (if we've hit min_confidence)."""
        self._logger.debug("Confidence threshold met; skipping remaining sources")
        with self._queues.lock:
            for source in self.sources:
                source.skip()
            self.finished = True

    def enqueue(self, urls, exclude_check=None):
        """Put a list of URLs into the various worker queues.

        *exclude_check* is an optional exclusion function that takes a URL and
        returns ``True`` if we should skip it and ``False`` otherwise.
        """
        for url in urls:
            with self._queues.lock:
                if url in self._handled_urls:
                    continue
                self._handled_urls.add(url)

                source = CopyvioSource(url=url, **self._source_args)
                self.sources.append(source)

                if exclude_check and exclude_check(url):
                    self._logger.debug(u"enqueue(): exclude {0}".format(url))
                    source.excluded = True
                    source.skip()
                    continue
                if self._short_circuit and self.finished:
                    self._logger.debug(u"enqueue(): auto-skip {0}".format(url))
                    source.skip()
                    continue

                try:
                    key = tldextract.extract(url).registered_domain
                except ImportError:  # Fall back on very naive method
                    from urlparse import urlparse
                    key = u".".join(urlparse(url).netloc.split(".")[-2:])

                logmsg = u"enqueue(): {0} {1} -> {2}"
                if key in self._queues.sites:
                    self._logger.debug(logmsg.format("append", key, url))
                    self._queues.sites[key].append(source)
                else:
                    self._logger.debug(logmsg.format("new", key, url))
                    self._queues.sites[key] = queue = deque()
                    queue.append(source)
                    self._queues.unassigned.put((key, queue))

    def compare(self, source, source_chain):
        """Compare a source to the article; call _finish_early if necessary."""
        if source_chain:
            delta = MarkovChainIntersection(self._article, source_chain)
            conf = self._calculate_confidence(delta)
        else:
            conf = 0.0
        self._logger.debug(u"compare(): {0} -> {1}".format(source.url, conf))
        with self._finish_lock:
            if source_chain:
                source.update(conf, source_chain, delta)
            source.finish_work()
            if not self.finished and conf >= self._min_confidence:
                if self._short_circuit:
                    self._finish_early()
                else:
                    self.finished = True

    def wait(self):
        """Wait for the workers to finish handling the sources."""
        self._logger.debug("Waiting on {0} sources".format(len(self.sources)))
        for source in self.sources:
            source.join(self._until)
        with self._finish_lock:
            pass  # Wait for any remaining comparisons to be finished
        if not _is_globalized:
            for i in xrange(self._num_workers):
                self._queues.unassigned.put((StopIteration, None))

    def get_result(self, num_queries=0):
        """Return a CopyvioCheckResult containing the results of this check."""
        def cmpfunc(s1, s2):
            if s2.confidence != s1.confidence:
                return 1 if s2.confidence > s1.confidence else -1
            if s2.excluded != s1.excluded:
                return 1 if s1.excluded else -1
            return int(s1.skipped) - int(s2.skipped)

        self.sources.sort(cmpfunc)
        return CopyvioCheckResult(self.finished, self.sources, num_queries,
                                  time() - self._start_time, self._article,
                                  self.possible_miss)
