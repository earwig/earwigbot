# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from functools import partial
from gzip import GzipFile
from json import loads
from StringIO import StringIO
from time import sleep, time
from urllib import quote_plus, urlencode
from urllib2 import build_opener, URLError

try:
    import oauth2 as oauth
except ImportError:
    oauth = None

from earwigbot.wiki.exceptions import *

class CopyvioCheckResult(object):
    def __init__(self, violation, confidence, url, queries):
        self.violation = violation
        self.confidence = confidence
        self.url = url
        self.queries = queries

    def __repr__(self):
        r = "CopyvioCheckResult(violation={0!r}, confidence={1!r}, url={2!r}, queries={3|r})"
        return r.format(self.violation, self.confidence, self.url, self.queries)


class CopyrightMixin(object):
    """
    EarwigBot's Wiki Toolset: Copyright Violation Mixin

    This is a mixin that provides one public method, copyvio_check(), which
    checks the page for copyright violations using a search engine API. The
    API keys must be provided to the method as arguments.
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

    def _select_search_engine(self, engine, credentials):
        """Return a function that can be called to do web searches.

        The "function" is a functools.partial object that takes one argument, a
        query, and returns a list of URLs, ranked by importance. The underlying
        logic depends on the 'engine' argument; for example, if 'engine' is
        "Yahoo! BOSS", we'll use self._yahoo_boss_query for querying.

        Raises UnknownSearchEngineError if 'engine' is not known to us, and
        UnsupportedSearchEngineError if we are missing a required package or
        module, like oauth2 for "Yahoo! BOSS".
        """
        if engine == "Yahoo! BOSS":
            if not oauth:
                e = "The package 'oauth2' could not be imported"
                raise UnsupportedSearchEngineError(e)
            searcher = self._yahoo_boss_query
        else:
            raise UnknownSearchEngineError(engine)

        return partial(searcher, credentials)

    def _yahoo_boss_query(self, cred, query):
        """Do a Yahoo! BOSS web search for 'query' using 'cred' as credentials.

        Returns a list of URLs, no more than fifty, ranked by relevance (as
        determined by Yahoo). Raises SearchQueryError() on errors.
        """
        base_url = "http://yboss.yahooapis.com/ysearch/web"
        query = quote_plus(query.join('"', '"'))
        params = {"q": query, "style": "raw", "format": "json"}
        url = "{0}?{1}".format(base_url, urlencode(params))

        consumer = oauth.Consumer(key=cred["key"], secret=cred["secret"])
        client = oauth.Client(consumer)
        headers, body = client.request(url, "GET")

        if headers["status"] != "200":
            e = "Yahoo! BOSS Error: got response code '{0}':\n{1}'"
            raise SearchQueryError(e.format(headers["status"], body))

        try:
            res = loads(body)
        except ValueError:
            e = "Yahoo! BOSS Error: JSON could not be decoded"
            raise SearchQueryError(e)

        try:
            results = res["bossresponse"]["web"]["results"]
        except KeyError:
            return []
        return [result["url"] for result in results]

    def _copyvio_strip_content(self, content):
        return content

    def _copyvio_chunk_content(self, content):
        return [content]

    def _copyvio_compare_content(self, content, url):
        html = self._open_url_ignoring_errors(url)
        if not html:
            return 0

        confidence = 0
        return confidence

    def copyvio_check(self, engine, credentials, min_confidence=0.75,
                      max_queries=-1, interquery_sleep=1, force=False):
        """Check the page for copyright violations.

        Returns a CopyvioCheckResult object, with four useful attributes:
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
        search = self._select_search_engine(engine, credentials)
        handled_urls = []
        best_confidence = 0
        best_match = None
        num_queries = 0
        content = self.get(force)
        clean = self._copyvio_strip_content(content)
        chunks = self._copyvio_chunk_content(clean)
        last_query = time()

        while (chunks and best_confidence < min_confidence and
               (max_queries < 0 or num_queries < max_queries)):
            urls = search(chunks.pop(0))
            urls = [url for url in urls if url not in handled_urls]
            for url in urls:
                handled_urls.append(url)
                confidence = self._copyvio_compare_content(content, url)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = url
            num_queries += 1
            diff = time() - last_query
            if diff < interquery_sleep:
                sleep(interquery_sleep - diff)
            last_query = time()

        if best_confidence >= min_confidence:  # violation?
            vi = True
        else:
            vi = False
        return CopyvioCheckResult(vi, best_confidence, best_match, num_queries)
