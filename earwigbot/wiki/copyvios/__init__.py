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
from Queue import Empty, Queue
from socket import timeout
from StringIO import StringIO
from threading import Lock, Thread
from time import sleep, time
from urllib2 import build_opener, URLError

from earwigbot import exceptions, importer
from earwigbot.wiki.copyvios.markov import (
    EMPTY, EMPTY_INTERSECTION, MarkovChain, MarkovChainIntersection)
from earwigbot.wiki.copyvios.parsers import ArticleTextParser, HTMLTextParser
from earwigbot.wiki.copyvios.result import CopyvioCheckResult
from earwigbot.wiki.copyvios.search import YahooBOSSSearchEngine

oauth = importer.new("oauth2")

__all__ = ["CopyvioMixIn"]

_WorkingResult = namedtuple("_WorkingResult", ["url", "confidence", "chains"])

class _CopyvioWorkspace(object):
    """Manages a single copyvio check distributed across threads."""

    def __init__(self, article, min_confidence, until, logger, headers,
                 url_timeout=5):
        self.best = _WorkingResult(None, 0.0, (EMPTY, EMPTY_INTERSECTION))
        self.until = until

        self._article = article
        self._handled_urls = []
        self._headers = headers
        self._logger = logger.getChild("copyvios")
        self._min_confidence = min_confidence
        self._queue = Queue()
        self._result_lock = Lock()
        self._url_timeout = url_timeout
        self._workers = []

    def _calculate_confidence(self, delta):
        """Return the confidence of a violation as a float between 0 and 1."""
        return float(delta.size()) / self._article.size()

    def _finish_early(self):
        """Finish handling links prematurely, e.g. if we've met min confidence.

        This works by inserting an additional ``None`` into the queue (the
        "exit" signal for workers) and then dequeueing until we reach the first
        ``None``. This way, every worker will dequeue an exit signal signal on
        their next turn.
        """
        self._queue.put(None)
        try:
            while self._queue.get(block=False):
                pass
        except Empty:  # Might happen if we haven't called wait() yet, but NBD.
            pass

    def spawn(self, workers):
        """Spawn *workers* number of worker threads."""
        for i in xrange(workers):
            worker = _CopyvioWorker(self, self._headers, self._url_timeout)
            thread = Thread(target=worker.run)
            thread.daemon = True
            thread.start()
            self._workers.append(thread)

    def enqueue(self, urls, exclude_check=None):
        """Put a list of URLs into the worker queue.

        *exclude_check* is an optional exclusion function that takes a URL and
        returns ``True`` if we should skip it and ``False`` otherwise.
        """
        for url in urls:
            if url in self._handled_urls:
                continue
            self._handled_urls.append(url)
            if exclude_check and exclude_check(url):
                continue
            self._queue.put(url)

    def dequeue(self, max_time=None):
        """Get an element from the worker queue, with an optional timeout."""
        return self._queue.get(timeout=max_time)

    def wait(self):
        """Wait for the workers to finish handling the queue."""
        for i in xrange(len(self._workers)):
            self._queue.put(None)  # Exit signal to workers
        for worker in self._workers:
            worker.join()

    def compare(self, url, source):
        """Compare a source to the article, and update the working result."""
        delta = MarkovChainIntersection(self._article, source)
        confidence = self._calculate_confidence(delta)
        self._logger.debug("{0} -> {1}".format(url, confidence))
        with self._result_lock:
            if confidence > self.best.confidence:
                self.best = _WorkingResult(url, confidence, (source, delta))
                if confidence >= self._min_confidence:
                    self._finish_early()


class _CopyvioWorker(object):
    """A multithreaded URL opener/parser instance."""

    def __init__(self, workspace, headers, url_timeout):
        self._workspace = workspace
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
        try:
            response = self._opener.open(url, timeout=self._url_timeout)
            result = response.read()
        except (URLError, timeout):
            return None

        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(result)
            gzipper = GzipFile(fileobj=stream)
            try:
                result = gzipper.read()
            except IOError:
                return None

        ctype_full = response.headers.get("Content-Type", "text/plain")
        ctype = ctype_full.split(";", 1)[0]
        if ctype in ["text/html", "application/xhtml+xml"]:
            return HTMLTextParser(result).strip()
        elif ctype == "text/plain":
            return result.strip()
        else:
            return None

    def run(self):
        """Main entry point for the worker.

        We will keep fetching URLs from the queue and handling them until
        either we run out of time, or we get an exit signal that the queue is
        now empty.
        """
        while True:
            if self._workspace.until:
                max_time = self._workspace.until - time()
                if max_time <= 0:
                    return
                try:
                    url = self._workspace.dequeue(max_time)
                except Empty:
                    return
            else:
                url = self._workspace.dequeue()
            if url is None:  # Exit signal from workspace.wait()
                return
            text = self._open_url(url.encode("utf8"))
            if text:
                self._workspace.compare(url, MarkovChain(text))


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

    def copyvio_check(self, min_confidence=0.5, max_queries=15, max_time=-1,
                      worker_threads=4):
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

        *worker_threads* is the number of threads we will spawn to handle URL
        fetching and parsing simultaneously. Between 1 and 8 is recommended.

        Raises :exc:`.CopyvioCheckError` or subclasses
        (:exc:`.UnknownSearchEngineError`, :exc:`.SearchQueryError`, ...) on
        errors.
        """
        start_time = time()
        until = (start_time + max_time) if max_time > 0 else None
        searcher = self._get_search_engine()
        parser = ArticleTextParser(self.get())
        article = MarkovChain(parser.strip())
        workspace = _CopyvioWorkspace(article, min_confidence,
                                      until, self._logger, self._addheaders)
        if self._exclusions_db:
            self._exclusions_db.sync(self.site.name)
            exclude = lambda u: self._exclusions_db.check(self.site.name, u)
        else:
            exclude = None

        if article.size() < 20:  # Auto-fail very small articles
            result = CopyvioCheckResult(False, 0.0, None, 0, 0, article,
                                        workspace.best.chains)
            self._logger.info(result.get_log_message(self.title))
            return result

        workspace.spawn(worker_threads)
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

    def copyvio_compare(self, url, min_confidence=0.5, max_time=30):
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
        start_time = time()
        until = (start_time + max_time) if max_time > 0 else None
        article = MarkovChain(ArticleTextParser(self.get()).strip())
        workspace = _CopyvioWorkspace(article, min_confidence,
                                      until, self._logger, self._addheaders)
        workspace.enqueue([url])
        workspace.spawn(1)
        workspace.wait()
        url, conf, chains = workspace.best
        result = CopyvioCheckResult(conf >= min_confidence, conf, url, 0,
                                    time() - start_time, article, chains)
        self._logger.info(result.get_log_message(self.title))
        return result
