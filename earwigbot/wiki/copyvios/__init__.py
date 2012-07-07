# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from gzip import GzipFile
from StringIO import StringIO
from time import sleep, time
from urllib2 import build_opener, URLError

try:
    import oauth2 as oauth
except ImportError:
    oauth = None

from earwigbot import exceptions
from earwigbot.wiki.copyvios.markov import MarkovChain, MarkovChainIntersection
from earwigbot.wiki.copyvios.parsers import ArticleTextParser, HTMLTextParser
from earwigbot.wiki.copyvios.search import YahooBOSSSearchEngine

__all__ = ["CopyvioCheckResult", "CopyvioMixIn"]

class CopyvioCheckResult(object):
    def __init__(self, violation, confidence, url, queries, article, chains):
        self.violation = violation
        self.confidence = confidence
        self.url = url
        self.queries = queries
        self.article_chain = article
        self.source_chain = chains[0]
        self.delta_chain = chains[1]

    def __repr__(self):
        """Return the canonical string representation of the result."""
        res = "CopyvioCheckResult(violation={0!r}, confidence={1!r}, url={2!r}, queries={3|r})"
        return res.format(self.violation, self.confidence, self.url,
                          self.queries)

    def __str__(self):
        """Return a nice string representation of the result."""
        res = "<CopyvioCheckResult ({0} with {1} conf)>"
        return res.format(self.violation, self.confidence)


class CopyvioMixIn(object):
    """
    EarwigBot's Wiki Toolset: Copyright Violation Mixin

    This is a mixin that provides two public methods, copyvio_check() and
    copyvio_compare(). The former checks the page for copyright violations
    using a search engine API, and the latter compares the page against a
    specified URL. Credentials for the search engine API are stored in the
    site's config.
    """
    def __init__(self, site):
        self._opener = build_opener()
        self._opener.addheaders = site._opener.addheaders

    def _open_url_ignoring_errors(self, url):
        """Open a URL using self._opener and return its content, or None.

        Will decompress the content if the headers contain "gzip" as its
        content encoding, and will return None if URLError is raised while
        opening the URL. IOErrors while gunzipping a compressed response are
        ignored, and the original content is returned.
        """
        try:
            response = self._opener.open(url)
        except URLError:
            return None
        result = response.read()

        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(result)
            gzipper = GzipFile(fileobj=stream)
            try:
                result = gzipper.read()
            except IOError:
                pass

        return result

    def _select_search_engine(self):
        """Return a function that can be called to do web searches.

        The "function" is a functools.partial object that takes one argument, a
        query, and returns a list of URLs, ranked by importance. The underlying
        logic depends on the 'engine' argument; for example, if 'engine' is
        "Yahoo! BOSS", we'll use self._yahoo_boss_query for querying.

        Raises UnknownSearchEngineError if the 'engine' listed in our config is
        unknown to us, and UnsupportedSearchEngineError if we are missing a
        required package or module, like oauth2 for "Yahoo! BOSS".
        """
        engine, credentials = self._site._search_config

        if engine == "Yahoo! BOSS":
            if not oauth:
                e = "The package 'oauth2' could not be imported"
                raise exceptions.UnsupportedSearchEngineError(e)
            return YahooBOSSSearchEngine(credentials)

        raise exceptions.UnknownSearchEngineError(engine)

    def _copyvio_compare_content(self, article, url):
        """Return a number comparing an article and a URL.

        The *article* is a Markov chain, whereas the URL is a string that we
        will try to open ourselves.
        """
        html = self._open_url_ignoring_errors(url)
        if not html:
            return 0

        source = MarkovChain(HTMLTextParser(html).strip())
        delta = MarkovChainIntersection(article, source)
        return float(delta.size()) / article.size(), (source, delta)

    def copyvio_check(self, min_confidence=0.5, max_queries=-1,
                      interquery_sleep=1, force=False):
        """Check the page for copyright violations.

        Returns a _CopyvioCheckResult object with four useful attributes:
        "violation", "confidence", "url", and "queries". "confidence" is a
        number between 0 and 1; if it is less than "min_confidence", we could
        not find any indication of a violation (so "violation" will be False
        and "url" may or may not be None), otherwise it indicates the relative
        faith in our results, "violation" will be True, and "url" will be the
        place the article is suspected of being copied from. "queries" is the
        number of queries used to determine the results.

        "max_queries" is self-explanatory; we will never make more than this
        number of queries in a given check. If it's less than 0, we will not
        limit our number of queries.

        "interquery_sleep" is the minimum amount of time we will sleep between
        search engine queries, in seconds.

        "force" is simply passed to page.get() - it has the same behavior there
        as it does here.

        Raises CopyvioCheckError or subclasses (UnknownSearchEngineError,
        SearchQueryError, ...) on errors.
        """
        searcher = self._select_search_engine()
        handled_urls = []
        best_confidence = 0
        best_match = None
        num_queries = 0
        empty = MarkovChain("")
        best_chains = (empty, MarkovChainIntersection(empty, empty))
        content = self.get(force)
        clean = ArticleTextParser(content).strip()
        chunks = ArticleTextParser(clean).chunk(max_queries)
        article_chain = MarkovChain(clean)
        last_query = time()

        if article_chain.size() < 20:  # Auto-fail very small articles
            return CopyvioCheckResult(False, best_confidence, best_match,
                                      num_queries, article_chain, best_chains)

        while (chunks and best_confidence < min_confidence and
               (max_queries < 0 or num_queries < max_queries)):
            urls = searcher.search(chunks.pop(0))
            urls = [url for url in urls if url not in handled_urls]
            for url in urls:
                handled_urls.append(url)
                conf, chains = self._copyvio_compare_content(article_chain, url)
                if conf > best_confidence:
                    best_confidence = conf
                    best_match = url
                    best_chains = chains
            num_queries += 1
            diff = time() - last_query
            if diff < interquery_sleep:
                sleep(interquery_sleep - diff)
            last_query = time()

        if best_confidence >= min_confidence:  # violation?
            v = True
        else:
            v = False
        return CopyvioCheckResult(v, best_confidence, best_match, num_queries,
                                  article_chain, best_chains)

    def copyvio_compare(self, url, min_confidence=0.5, force=False):
        """Check the page like copyvio_check(), but against a specific URL.

        This is essentially a reduced version of the above - a copyivo
        comparison is made using Markov chains and the result is returned in a
        _CopyvioCheckResult object - without using a search engine, as the
        suspected "violated" URL is supplied from the start.

        Its primary use is to generate a result when the URL is retrieved from
        a cache, like the one used in EarwigBot's Toolserver site. After a
        search is done, the resulting URL is stored in a cache for 24 hours so
        future checks against that page will not require another set of
        time-and-money-consuming search engine queries. However, the comparison
        itself (which includes the article's and the source's content) cannot
        be stored for data retention reasons, so a fresh comparison is made
        using this function.

        Since no searching is done, neither UnknownSearchEngineError nor
        SearchQueryError will be raised.
        """
        content = self.get(force)
        clean = ArticleTextParser(content).strip()
        article_chain = MarkovChain(clean)
        confidence, chains = self._copyvio_compare_content(article_chain, url)

        if confidence >= min_confidence:
            is_violation = True
        else:
            is_violation = False
        return CopyvioCheckResult(is_violation, confidence, url, 0,
                                  article_chain, chains)
