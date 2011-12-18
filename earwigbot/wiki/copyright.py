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

from json import loads
from time import sleep, time
from urllib import quote_plus, urlencode

try:
    import oauth2 as oauth
except ImportError:
    oauth = None

from earwigbot.wiki.exceptions import *

class CopyvioCheckResult(object):
    def __init__(self, confidence, url, queries):
        self.confidence = confidence
        self.url = url
        self.queries = queries

    def __repr__(self):
        r = "CopyvioCheckResult(confidence={0!r}, url={1!r}, queries={2|r})"
        return r.format(self.confidence, self.url, self.queries)


class CopyrightMixin(object):
    """
    EarwigBot's Wiki Toolset: Copyright Violation Mixin

    This is a mixin that provides one public method, copyvio_check(), which
    checks the page for copyright violations using a search engine API. The
    API keys must be provided to the method as arguments.
    """
    def _yahoo_boss_query(self, query, cred):
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

    def _copyvio_explode_content(self, content):
        return content

    def _copyvio_compare_content(self, content, url):
        return 0

    def copyvio_check(self, engine, credentials, min_confidence=0.5,
                      max_queries=-1, interquery_sleep=1, force=False):
        """Check the page for copyright violations.

        Returns a CopyvioCheckResult object, with three useful attributes:
        "confidence", "url", and "queries". "confidence" is a number between
        0 and 1; if it is less than min_confidence, we could not find any
        indication of a violation (so "url" will be None), otherwise it
        indicates the relative faith in our results, and "url" will be the
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
        if engine == "Yahoo! BOSS":
            if not oauth:
                e = "The package 'oauth2' could not be imported"
                raise UnsupportedSearchEngineError(e)
            querier = self._yahoo_boss_query
        else:
            raise UnknownSearchEngineError(engine)

        handled_urls = []
        best_confidence = 0
        best_match = None
        num_queries = 0
        content = self.get(force)
        clean = self._copyvio_strip_content(content)
        fragments = self._copyvio_explode_content(clean)
        last_query = time()

        while (fragments and best_confidence < min_confidence and
               (max_queries < 0 or num_queries < max_queries)):
            urls = querier(fragments.pop(0), credentials)
            urls = [url for url in urls if url not in handled_urls]
            for url in urls:
                confidence = self._copyvio_compare_content(content, url)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = url
            num_queries += 1
            diff = time() - last_query
            if diff < interquery_sleep:
                sleep(interquery_sleep - diff)
            last_query = time()

        return CopyvioCheckResult(best_confidence, best_match, num_queries)
