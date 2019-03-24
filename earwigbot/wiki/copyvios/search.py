# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2016 Ben Kurtovic <ben.kurtovic@gmail.com>
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
from json import loads
from re import sub as re_sub
from socket import error
from StringIO import StringIO
from urllib import quote, urlencode
from urllib2 import URLError

from earwigbot import importer
from earwigbot.exceptions import SearchQueryError

lxml = importer.new("lxml")
oauth = importer.new("oauth2")

__all__ = ["BingSearchEngine", "GoogleSearchEngine", "YahooBOSSSearchEngine",
           "YandexSearchEngine", "SEARCH_ENGINES"]

class _BaseSearchEngine(object):
    """Base class for a simple search engine interface."""
    name = "Base"

    def __init__(self, cred, opener):
        """Store credentials (*cred*) and *opener* for searching later on."""
        self.cred = cred
        self.opener = opener
        self.count = 5

    def __repr__(self):
        """Return the canonical string representation of the search engine."""
        return "{0}()".format(self.__class__.__name__)

    def __str__(self):
        """Return a nice string representation of the search engine."""
        return "<{0}>".format(self.__class__.__name__)

    def _open(self, *args):
        """Open a URL (like urlopen) and try to return its contents."""
        try:
            response = self.opener.open(*args)
            result = response.read()
        except (URLError, error) as exc:
            raise SearchQueryError("{0} Error: {1}".format(self.name, exc))

        if response.headers.get("Content-Encoding") == "gzip":
            stream = StringIO(result)
            gzipper = GzipFile(fileobj=stream)
            result = gzipper.read()

        code = response.getcode()
        if code != 200:
            err = "{0} Error: got response code '{1}':\n{2}'"
            raise SearchQueryError(err.format(self.name, code, result))

        return result

    @staticmethod
    def requirements():
        """Return a list of packages required by this search engine."""
        return []

    def search(self, query):
        """Use this engine to search for *query*.

        Not implemented in this base class; overridden in subclasses.
        """
        raise NotImplementedError()


class BingSearchEngine(_BaseSearchEngine):
    """A search engine interface with Bing Search (via Azure Marketplace)."""
    name = "Bing"

    def __init__(self, cred, opener):
        super(BingSearchEngine, self).__init__(cred, opener)

        key = self.cred["key"]
        auth = (key + ":" + key).encode("base64").replace("\n", "")
        self.opener.addheaders.append(("Authorization", "Basic " + auth))

    def search(self, query):
        """Do a Bing web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Bing).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        service = "SearchWeb" if self.cred["type"] == "searchweb" else "Search"
        url = "https://api.datamarket.azure.com/Bing/{0}/Web?".format(service)
        params = {
            "$format": "json",
            "$top": str(self.count),
            "Query": "'\"" + query.replace('"', "").encode("utf8") + "\"'",
            "Market": "'en-US'",
            "Adult": "'Off'",
            "Options": "'DisableLocationDetection'",
            "WebSearchOptions": "'DisableHostCollapsing+DisableQueryAlterations'"
        }

        result = self._open(url + urlencode(params))

        try:
            res = loads(result)
        except ValueError:
            err = "Bing Error: JSON could not be decoded"
            raise SearchQueryError(err)

        try:
            results = res["d"]["results"]
        except KeyError:
            return []
        return [result["Url"] for result in results]


class GoogleSearchEngine(_BaseSearchEngine):
    """A search engine interface with Google Search."""
    name = "Google"

    def search(self, query):
        """Do a Google web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Google).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        domain = self.cred.get("proxy", "www.googleapis.com")
        url = "https://{0}/customsearch/v1?".format(domain)
        params = {
            "cx": self.cred["id"],
            "key": self.cred["key"],
            "q": '"' + query.replace('"', "").encode("utf8") + '"',
            "alt": "json",
            "num": str(self.count),
            "safe": "off",
            "fields": "items(link)"
        }

        result = self._open(url + urlencode(params))

        try:
            res = loads(result)
        except ValueError:
            err = "Google Error: JSON could not be decoded"
            raise SearchQueryError(err)

        try:
            return [item["link"] for item in res["items"]]
        except KeyError:
            return []


class YahooBOSSSearchEngine(_BaseSearchEngine):
    """A search engine interface with Yahoo! BOSS."""
    name = "Yahoo! BOSS"

    @staticmethod
    def _build_url(base, params):
        """Works like urllib.urlencode(), but uses %20 for spaces over +."""
        enc = lambda s: quote(s.encode("utf8"), safe="")
        args = ["=".join((enc(k), enc(v))) for k, v in params.iteritems()]
        return base + "?" + "&".join(args)

    @staticmethod
    def requirements():
        return ["oauth2"]

    def search(self, query):
        """Do a Yahoo! BOSS web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Yahoo).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        key, secret = self.cred["key"], self.cred["secret"]
        consumer = oauth.Consumer(key=key, secret=secret)

        url = "http://yboss.yahooapis.com/ysearch/web"
        params = {
            "oauth_version": oauth.OAUTH_VERSION,
            "oauth_nonce": oauth.generate_nonce(),
            "oauth_timestamp": oauth.Request.make_timestamp(),
            "oauth_consumer_key": consumer.key,
            "q": '"' + query.encode("utf8") + '"',
            "count": str(self.count),
            "type": "html,text,pdf",
            "format": "json",
        }

        req = oauth.Request(method="GET", url=url, parameters=params)
        req.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)

        result = self._open(self._build_url(url, req))

        try:
            res = loads(result)
        except ValueError:
            err = "Yahoo! BOSS Error: JSON could not be decoded"
            raise SearchQueryError(err)

        try:
            results = res["bossresponse"]["web"]["results"]
        except KeyError:
            return []
        return [result["url"] for result in results]


class YandexSearchEngine(_BaseSearchEngine):
    """A search engine interface with Yandex Search."""
    name = "Yandex"

    @staticmethod
    def requirements():
        return ["lxml.etree"]

    def search(self, query):
        """Do a Yandex web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Yandex).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        domain = self.cred.get("proxy", "yandex.com")
        url = "https://{0}/search/xml?".format(domain)
        query = re_sub(r"[^a-zA-Z0-9 ]", "", query).encode("utf8")
        params = {
            "user": self.cred["user"],
            "key": self.cred["key"],
            "query": '"' + query + '"',
            "l10n": "en",
            "filter": "none",
            "maxpassages": "1",
            "groupby": "mode=flat.groups-on-page={0}".format(self.count)
        }

        result = self._open(url + urlencode(params))

        try:
            data = lxml.etree.fromstring(result)
            return [elem.text for elem in data.xpath(".//url")]
        except lxml.etree.Error as exc:
            raise SearchQueryError("Yandex XML parse error: " + str(exc))


SEARCH_ENGINES = {
    "Bing": BingSearchEngine,
    "Google": GoogleSearchEngine,
    "Yahoo! BOSS": YahooBOSSSearchEngine,
    "Yandex": YandexSearchEngine
}
