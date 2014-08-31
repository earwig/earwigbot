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

from time import sleep, time
from urllib2 import build_opener

from earwigbot import exceptions, importer
from earwigbot.wiki.copyvios.markov import MarkovChain
from earwigbot.wiki.copyvios.parsers import ArticleTextParser
from earwigbot.wiki.copyvios.result import CopyvioCheckResult
from earwigbot.wiki.copyvios.search import YahooBOSSSearchEngine
from earwigbot.wiki.copyvios.workers import (
    globalize, localize, CopyvioWorkspace)

oauth = importer.new("oauth2")

__all__ = ["CopyvioMixIn", "globalize", "localize"]

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
        workspace = CopyvioWorkspace(article, min_confidence, until,
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
        workspace = CopyvioWorkspace(article, min_confidence, until,
                                     self._logger, self._addheaders, max_time)
        workspace.enqueue([url])
        workspace.wait()
        best = workspace.best
        result = CopyvioCheckResult(best.confidence >= min_confidence,
                                    best.confidence, best.url, 0,
                                    time() - start_time, article, best.chains)
        self._logger.info(result.get_log_message(self.title))
        return result
