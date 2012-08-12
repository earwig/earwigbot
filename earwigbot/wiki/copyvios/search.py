# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

import oauth2 as oauth

from earwigbot.exceptions import SearchQueryError

__all__ = ["BaseSearchEngine", "YahooBOSSSearchEngine"]

class BaseSearchEngine(object):
    """Base class for a simple search engine interface."""
    name = "Base"

    def __init__(self, cred):
        """Store credentials *cred* for searching later on."""
        self.cred = cred

    def __repr__(self):
        """Return the canonical string representation of the search engine."""
        return "{0}()".format(self.__class__.__name__)

    def __str__(self):
        """Return a nice string representation of the search engine."""
        return "<{0}>".format(self.__class__.__name__)

    def search(self, query):
        """Use this engine to search for *query*.

        Not implemented in this base class; overridden in subclasses.
        """
        raise NotImplementedError()


class YahooBOSSSearchEngine(BaseSearchEngine):
    """A search engine interface with Yahoo! BOSS."""
    name = "Yahoo! BOSS"

    def search(self, query):
        """Do a Yahoo! BOSS web search for *query*.

        Returns a list of URLs, no more than fifty, ranked by relevance (as
        determined by Yahoo). Raises
        :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        base_url = "http://yboss.yahooapis.com/ysearch/web"
        query = quote_plus(query.join('"', '"'))
        params = {"q": query, "type": "html,text", "format": "json"}
        url = "{0}?{1}".format(base_url, urlencode(params))

        consumer = oauth.Consumer(key=self.cred["key"],
                                  secret=self.cred["secret"])
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
