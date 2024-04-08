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
from io import StringIO
from json import loads
from re import sub as re_sub
from urllib.error import URLError
from urllib.parse import urlencode

from earwigbot import importer
from earwigbot.exceptions import SearchQueryError

lxml = importer.new("lxml")

__all__ = [
    "BingSearchEngine",
    "GoogleSearchEngine",
    "YandexSearchEngine",
    "SEARCH_ENGINES",
]


class _BaseSearchEngine:
    """Base class for a simple search engine interface."""

    name = "Base"

    def __init__(self, cred, opener):
        """Store credentials (*cred*) and *opener* for searching later on."""
        self.cred = cred
        self.opener = opener
        self.count = 5

    def __repr__(self):
        """Return the canonical string representation of the search engine."""
        return f"{self.__class__.__name__}()"

    def __str__(self):
        """Return a nice string representation of the search engine."""
        return f"<{self.__class__.__name__}>"

    def _open(self, *args):
        """Open a URL (like urlopen) and try to return its contents."""
        try:
            response = self.opener.open(*args)
            result = response.read()
        except (OSError, URLError) as exc:
            err = SearchQueryError(f"{self.name} Error: {exc}")
            err.cause = exc
            raise err

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
        super().__init__(cred, opener)

        key = self.cred["key"]
        auth = (key + ":" + key).encode("base64").replace("\n", "")
        self.opener.addheaders.append(("Authorization", "Basic " + auth))

    def search(self, query):
        """Do a Bing web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Bing).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        service = "SearchWeb" if self.cred["type"] == "searchweb" else "Search"
        url = f"https://api.datamarket.azure.com/Bing/{service}/Web?"
        params = {
            "$format": "json",
            "$top": str(self.count),
            "Query": "'\"" + query.replace('"', "").encode("utf8") + "\"'",
            "Market": "'en-US'",
            "Adult": "'Off'",
            "Options": "'DisableLocationDetection'",
            "WebSearchOptions": "'DisableHostCollapsing+DisableQueryAlterations'",
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
        url = f"https://{domain}/customsearch/v1?"
        params = {
            "cx": self.cred["id"],
            "key": self.cred["key"],
            "q": '"' + query.replace('"', "").encode("utf8") + '"',
            "alt": "json",
            "num": str(self.count),
            "safe": "off",
            "fields": "items(link)",
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
        url = f"https://{domain}/search/xml?"
        query = re_sub(r"[^a-zA-Z0-9 ]", "", query).encode("utf8")
        params = {
            "user": self.cred["user"],
            "key": self.cred["key"],
            "query": '"' + query + '"',
            "l10n": "en",
            "filter": "none",
            "maxpassages": "1",
            "groupby": f"mode=flat.groups-on-page={self.count}",
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
    "Yandex": YandexSearchEngine,
}
