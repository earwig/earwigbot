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
from urllib import quote_plus, urlencode

try:
    import oauth2 as oauth
except ImportError:
    oauth = None

from earwigbot.wiki.exceptions import *

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
        params = {"q": quote_plus(query), "style": "raw", "format": "json"}
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

    def copyvio_check(self, engine, credentials, force=False):
        """Check the page for copyright violations."""
        if engine == "Yahoo! BOSS":
            if not oauth:
                e = "The package 'oauth2' could not be imported"
                raise UnsupportedSearchEngineError(e)
            querier = self._yahoo_boss_query
        else:
            raise UnknownSearchEngineError(engine)
        content = self.get(force)
        return querier(content, credentials)
