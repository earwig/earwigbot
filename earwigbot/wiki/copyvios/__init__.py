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

from collections import namedtuple
from gzip import GzipFile
from math import log
from Queue import Empty, Queue
from socket import error
from StringIO import StringIO
from threading import Lock, Semaphore, Thread
from time import sleep, time
from urllib2 import build_opener, URLError

from earwigbot import exceptions, importer
from earwigbot.wiki.copyvios.markov import (
    EMPTY, EMPTY_INTERSECTION, MarkovChain, MarkovChainIntersection)
from earwigbot.wiki.copyvios.parsers import ArticleTextParser, HTMLTextParser
from earwigbot.wiki.copyvios.result import CopyvioCheckResult
from earwigbot.wiki.copyvios.search import YahooBOSSSearchEngine

oauth = importer.new("oauth2")
tldextract = importer.new("tldextract")

__all__ = ["CopyvioMixIn"]

_WorkingResult = namedtuple("_WorkingResult", ["url", "confidence", "chains"])

class _CopyvioWorkspace(object):
    """Manages a single copyvio check distributed across threads."""

    def __init__(self, article, min_confidence, until, logger, headers,
                 url_timeout=5, max_concurrent_requests=6):
        self.best = _WorkingResult(None, 0.0, (EMPTY, EMPTY_INTERSECTION))
        self.request_semaphore = Semaphore(max_concurrent_requests)

        self._article = article
        self._logger = logger.getChild("copyvios")
        self._min_confidence = min_confidence
        self._handled_urls = []
        self._is_finished = False
        self._enqueue_lock = Lock()
        self._result_lock = Lock()

        self._workers = {}
        self._worker_args = (self, until, headers, url_timeout)

    def _calculate_confidence(self, delta):
        """Return the confidence of a violation as a float between 0 and 1."""
        def conf_with_article_and_delta(article, delta):
            """Calculate confidence using the article and delta chain sizes."""
            # This piecewise function, C_AΔ(Δ), was defined such that
            # confidence exhibits exponential growth until it reaches the
            # default "suspect" confidence threshold, at which point it
            # transitions to polynomial growth with lim (A/Δ)→1 C_AΔ(A,Δ) = 1.
            # A graph can be viewed here:
            # http://benkurtovic.com/static/article-delta_confidence_function.pdf
            ratio = delta / article
            if ratio <= 0.52763:
                return log(1 / (1 - ratio))
            else:
                return (-0.8939 * (ratio ** 2)) + (1.8948 * ratio) - 0.0009

        def conf_with_delta(delta):
            """Calculate confidence using just the delta chain size."""
            # This piecewise function, C_Δ(Δ), was derived from experimental
            # data using reference points at (0, 0), (100, 0.5), (250, 0.75),
            # (500, 0.9), and (1000, 0.95) with lim Δ→+∞ C_Δ(Δ) = 1.
            # A graph can be viewed here:
            # http://benkurtovic.com/static/delta_confidence_function.pdf
            if delta <= 100:
                return delta / (delta + 100)
            elif delta <= 250:
                return (delta - 25) / (delta + 50)
            elif delta <= 500:
                return (10.5 * delta - 750) / (10 * delta)
            else:
                return (delta - 50) / delta

        d_size = float(delta.size)
        return max(conf_with_article_and_delta(self._article.size, d_size),
                   conf_with_delta(d_size))

    def _finish_early(self):
        """Finish handling links prematurely (if we've hit min_confidence)."""
        self._logger.debug("Confidence threshold met; clearing worker queues")
        with self._enqueue_lock:
            for worker in self._workers.itervalues():
                with worker.queue.mutex:
                    worker.queue.queue.clear()
                    worker.queue.queue.append(None)
            self._is_finished = True

    def enqueue(self, urls, exclude_check=None):
        """Put a list of URLs into the worker queue.

        *exclude_check* is an optional exclusion function that takes a URL and
        returns ``True`` if we should skip it and ``False`` otherwise.
        """
        for url in urls:
            with self._enqueue_lock:
                if self._is_finished:
                    break
                if url in self._handled_urls:
                    continue
                self._handled_urls.append(url)
                if exclude_check and exclude_check(url):
                    continue

                try:
                    key = tldextract.extract(url).registered_domain
                except ImportError:  # Fall back on very naive method
                    from urlparse import urlparse
                    key = u".".join(urlparse(url).netloc.split(".")[-2:])

                logmsg = u"enqueue(): {0} {1} -> {2}"
                if key in self._workers:
                    self._logger.debug(logmsg.format("PUT", key, url))
                    self._workers[key].queue.put(url)
                else:
                    self._logger.debug(logmsg.format("NEW", key, url))
                    worker = _CopyvioWorker(*self._worker_args)
                    worker.queue.put(url)
                    worker.start(key.encode("utf8"))
                    self._workers[key] = worker

    def wait(self):
        """Wait for the workers to finish handling the queue."""
        self._logger.debug("Waiting on {0} workers".format(len(self._workers)))
        for worker in self._workers.itervalues():
            worker.queue.put(None)  # Exit signal to workers
        for worker in self._workers.itervalues():
            worker.join()

    def compare(self, url, source):
        """Compare a source to the article, and update the working result."""
        delta = MarkovChainIntersection(self._article, source)
        confidence = self._calculate_confidence(delta)
        self._logger.debug(u"compare(): {0} -> {1}".format(url, confidence))
        with self._result_lock:
            if confidence > self.best.confidence:
                self.best = _WorkingResult(url, confidence, (source, delta))
                if confidence >= self._min_confidence:
                    self._finish_early()


class _CopyvioWorker(object):
    """A multithreaded URL opener/parser instance."""

    def __init__(self, workspace, until, headers, url_timeout):
        self.queue = Queue()

        self._thread = None
        self._workspace = workspace
        self._until = until
        self._opener = build_opener()
        self._opener.addheaders = headers
        self._url_timeout = url_timeout

    def _open_url(self, url):
        """Open a URL and return its parsed content, or None.

        First, we will decompress the content if the headers contain "gzip" as
        its content encoding. Then, we will return the content stripped using
        an HTML parser if the headers indicate it is HTML, or return the
        content directly if it is plain text. If we don't understand the
        content type, we'll return None.

        If a URLError was raised while opening the URL or an IOError was raised
        while decompressing, None will be returned.
        """
        with self._workspace.request_semaphore:
            try:
                response = self._opener.open(url, timeout=self._url_timeout)
            except (URLError, error):
                return None

        try:
            size = int(response.headers.get("Content-Length", 0))
        except ValueError:
            return None
        if size > 1024 ** 2:  # Ignore URLs larger than a megabyte
            return None

        ctype_full = response.headers.get("Content-Type", "text/plain")
        ctype = ctype_full.split(";", 1)[0]
        if ctype in ["text/html", "application/xhtml+xml"]:
            handler = lambda res: HTMLTextParser(res).strip()
        elif ctype == "text/plain":
            handler = lambda res: res.strip()
        else:
            return None

        with self._workspace.request_semaphore:
            try:
                content = response.read()
            except (URLError, error):
                return None

        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(content)
            gzipper = GzipFile(fileobj=stream)
            try:
                content = gzipper.read(2 * 1024 ** 2)
            except IOError:
                return None

        return handler(content)

    def _run(self):
        """Main entry point for the worker thread.

        We will keep fetching URLs from the queue and handling them until
        either we run out of time, or we get an exit signal that the queue is
        now empty.
        """
        while True:
            if self._until:
                max_time = self._until - time()
                if max_time <= 0:
                    return
                try:
                    url = self.queue.get(timeout=max_time)
                except Empty:
                    return
            else:
                url = self.queue.get()
            if url is None:  # Exit signal
                return
            text = self._open_url(url.encode("utf8"))
            if text:
                self._workspace.compare(url, MarkovChain(text))

    def start(self, name):
        """Start the worker in a new thread, with a given name."""
        self._thread = thread = Thread(target=self._run)
        thread.name = "cvworker-" + name
        thread.daemon = True
        thread.start()

    def join(self):
        """Join to the worker thread, blocking until it finishes."""
        self._thread.join()


class CopyvioMixIn(object):
    """
    **EarwigBot: Wiki Toolset: Copyright Violation MixIn**

    This is a mixin that provides two public methods, :py:meth:`copyvio_check`
    and :py:meth:`copyvio_compare`. The former checks the page for copyright
    violations using a search engine API, and the latter compares the page
    against a given URL. Credentials for the search engine API are stored in
    the :py:class:`~earwigbot.wiki.site.Site`'s config.
    """

    def __init__(self, site):
        self._search_config = site._search_config
        self._exclusions_db = self._search_config.get("exclusions_db")
        self._addheaders = site._opener.addheaders

    def _get_search_engine(self):
        """Return a function that can be called to do web searches.

        The function takes one argument, a search query, and returns a list of
        URLs, ranked by importance. The underlying logic depends on the
        *engine* argument within our config; for example, if *engine* is
        "Yahoo! BOSS", we'll use YahooBOSSSearchEngine for querying.

        Raises UnknownSearchEngineError if the 'engine' listed in our config is
        unknown to us, and UnsupportedSearchEngineError if we are missing a
        required package or module, like oauth2 for "Yahoo! BOSS".
        """
        engine = self._search_config["engine"]
        credentials = self._search_config["credentials"]

        if engine == "Yahoo! BOSS":
            try:
                oauth.__version__  # Force-load the lazy module
            except ImportError:
                e = "Yahoo! BOSS requires the 'oauth2' package: https://github.com/simplegeo/python-oauth2"
                raise exceptions.UnsupportedSearchEngineError(e)
            opener = build_opener()
            opener.addheaders = self._addheaders
            return YahooBOSSSearchEngine(credentials, opener)

        raise exceptions.UnknownSearchEngineError(engine)

    def copyvio_check(self, min_confidence=0.75, max_queries=15, max_time=-1):
        """Check the page for copyright violations.

        Returns a :class:`.CopyvioCheckResult` object with information on the
        results of the check.

        *min_confidence* is the minimum amount of confidence we must have in
        the similarity between a source text and the article in order for us to
        consider it a suspected violation. This is a number between 0 and 1.

        *max_queries* is self-explanatory; we will never make more than this
        number of queries in a given check.

        *max_time* can be set to prevent copyvio checks from taking longer than
        a set amount of time (generally around a minute), which can be useful
        if checks are called through a web server with timeouts. We will stop
        checking new URLs as soon as this limit is reached.

        Raises :exc:`.CopyvioCheckError` or subclasses
        (:exc:`.UnknownSearchEngineError`, :exc:`.SearchQueryError`, ...) on
        errors.
        """
        log = u"Starting copyvio check for [[{0}]]"
        self._logger.info(log.format(self.title))
        start_time = time()
        until = (start_time + max_time) if max_time > 0 else None
        searcher = self._get_search_engine()
        parser = ArticleTextParser(self.get())
        article = MarkovChain(parser.strip())
        workspace = _CopyvioWorkspace(article, min_confidence, until,
                                      self._logger, self._addheaders)
        if self._exclusions_db:
            self._exclusions_db.sync(self.site.name)
            exclude = lambda u: self._exclusions_db.check(self.site.name, u)
        else:
            exclude = None

        if article.size < 20:  # Auto-fail very small articles
            result = CopyvioCheckResult(False, 0.0, None, 0, 0, article,
                                        workspace.best.chains)
            self._logger.info(result.get_log_message(self.title))
            return result

        workspace.enqueue(parser.get_links(), exclude)
        chunks = parser.chunk(self._search_config["nltk_dir"], max_queries)
        num_queries = 0
        for chunk in chunks:
            if workspace.best.confidence >= min_confidence:
                break
            log = u"[[{0}]] -> querying {1} for {2!r}"
            self._logger.debug(log.format(self.title, searcher.name, chunk))
            workspace.enqueue(searcher.search(chunk), exclude)
            num_queries += 1
            sleep(1)

        workspace.wait()
        result = CopyvioCheckResult(
            workspace.best.confidence >= min_confidence,
            workspace.best.confidence, workspace.best.url, num_queries,
            time() - start_time, article, workspace.best.chains)
        self._logger.info(result.get_log_message(self.title))
        return result

    def copyvio_compare(self, url, min_confidence=0.75, max_time=30):
        """Check the page like :py:meth:`copyvio_check` against a specific URL.

        This is essentially a reduced version of :meth:`copyvio_check` - a
        copyivo comparison is made using Markov chains and the result is
        returned in a :class:`.CopyvioCheckResult` object - but without using a
        search engine, since the suspected "violated" URL is supplied from the
        start.

        Its primary use is to generate a result when the URL is retrieved from
        a cache, like the one used in EarwigBot's Tool Labs site. After a
        search is done, the resulting URL is stored in a cache for 72 hours so
        future checks against that page will not require another set of
        time-and-money-consuming search engine queries. However, the comparison
        itself (which includes the article's and the source's content) cannot
        be stored for data retention reasons, so a fresh comparison is made
        using this function.

        Since no searching is done, neither :exc:`.UnknownSearchEngineError`
        nor :exc:`.SearchQueryError` will be raised.
        """
        log = u"Starting copyvio compare for [[{0}]] against {1}"
        self._logger.info(log.format(self.title, url))
        start_time = time()
        until = (start_time + max_time) if max_time > 0 else None
        article = MarkovChain(ArticleTextParser(self.get()).strip())
        workspace = _CopyvioWorkspace(article, min_confidence, until,
                                      self._logger, self._addheaders, max_time)
        workspace.enqueue([url])
        workspace.wait()
        url, conf, chains = workspace.best
        result = CopyvioCheckResult(conf >= min_confidence, conf, url, 0,
                                    time() - start_time, article, chains)
        self._logger.info(result.get_log_message(self.title))
        return result
