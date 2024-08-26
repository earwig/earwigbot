# Copyright (C) 2009-2024 Ben Kurtovic <ben.kurtovic@gmail.com>
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

__all__ = [
    "BingSearchEngine",
    "GoogleSearchEngine",
    "SearchEngine",
    "YandexSearchEngine",
    "get_search_engine",
]

import base64
import gzip
import io
import json
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any
from urllib.error import URLError

from earwigbot import exceptions


class SearchEngine(ABC):
    """Base class for a simple search engine interface."""

    name = "Base"

    def __init__(
        self, cred: dict[str, str], opener: urllib.request.OpenerDirector
    ) -> None:
        """Store credentials (*cred*) and *opener* for searching later on."""
        self.cred = cred
        self.opener = opener
        self.count = 5

    def __repr__(self) -> str:
        """Return the canonical string representation of the search engine."""
        return f"{self.__class__.__name__}()"

    def __str__(self) -> str:
        """Return a nice string representation of the search engine."""
        return f"<{self.__class__.__name__}>"

    def _open(self, url: str) -> bytes:
        """Open a URL (like urlopen) and try to return its contents."""
        try:
            response = self.opener.open(url)
            result = response.read()
        except (OSError, URLError) as exc:
            raise exceptions.SearchQueryError(f"{self.name} Error: {exc}")

        if response.headers.get("Content-Encoding") == "gzip":
            stream = io.BytesIO(result)
            gzipper = gzip.GzipFile(fileobj=stream)
            result = gzipper.read()

        code = response.getcode()
        if code != 200:
            raise exceptions.SearchQueryError(
                f"{self.name} Error: got response code '{code}':\n{result}'"
            )

        return result

    @staticmethod
    def requirements() -> list[str]:
        """Return a list of packages required by this search engine."""
        return []

    @abstractmethod
    def search(self, query: str) -> list[str]:
        """
        Use this engine to search for *query*.

        Not implemented in this base class; overridden in subclasses.
        """


class BingSearchEngine(SearchEngine):
    """A search engine interface with Bing Search (via Azure Marketplace)."""

    name = "Bing"

    def __init__(
        self, cred: dict[str, str], opener: urllib.request.OpenerDirector
    ) -> None:
        super().__init__(cred, opener)

        key = self.cred["key"]
        auth = base64.b64encode(f"{key}:{key}".encode()).decode()
        self.opener.addheaders.append(("Authorization", f"Basic {auth}"))

    def search(self, query: str) -> list[str]:
        """
        Do a Bing web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Bing).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        service = "SearchWeb" if self.cred["type"] == "searchweb" else "Search"
        url = f"https://api.datamarket.azure.com/Bing/{service}/Web?"
        params = {
            "$format": "json",
            "$top": str(self.count),
            "Query": "'\"" + query.replace('"', "") + "\"'",
            "Market": "'en-US'",
            "Adult": "'Off'",
            "Options": "'DisableLocationDetection'",
            "WebSearchOptions": "'DisableHostCollapsing+DisableQueryAlterations'",
        }

        result = self._open(url + urllib.parse.urlencode(params))

        try:
            res = json.loads(result)
        except ValueError:
            raise exceptions.SearchQueryError("Bing Error: JSON could not be decoded")

        try:
            results = res["d"]["results"]
        except KeyError:
            return []
        return [result["Url"] for result in results]


class GoogleSearchEngine(SearchEngine):
    """A search engine interface with Google Search."""

    name = "Google"

    def search(self, query: str) -> list[str]:
        """
        Do a Google web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Google).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        domain = self.cred.get("proxy", "www.googleapis.com")
        url = f"https://{domain}/customsearch/v1?"
        params = {
            "cx": self.cred["id"],
            "key": self.cred["key"],
            "q": '"' + query.replace('"', "") + '"',
            "alt": "json",
            "num": str(self.count),
            "safe": "off",
            "fields": "items(link)",
        }

        result = self._open(url + urllib.parse.urlencode(params))

        try:
            res = json.loads(result)
        except ValueError:
            err = "Google Error: JSON could not be decoded"
            raise exceptions.SearchQueryError(err)

        try:
            return [item["link"] for item in res["items"]]
        except KeyError:
            return []


class YandexSearchEngine(SearchEngine):
    """A search engine interface with Yandex Search."""

    name = "Yandex"

    @staticmethod
    def requirements():
        return ["lxml.etree"]

    def search(self, query: str) -> list[str]:
        """
        Do a Yandex web search for *query*.

        Returns a list of URLs ranked by relevance (as determined by Yandex).
        Raises :py:exc:`~earwigbot.exceptions.SearchQueryError` on errors.
        """
        import lxml.etree

        domain = self.cred.get("proxy", "yandex.com")
        url = f"https://{domain}/search/xml?"
        query = re.sub(r"[^a-zA-Z0-9 ]", "", query)
        params = {
            "user": self.cred["user"],
            "key": self.cred["key"],
            "query": '"' + query + '"',
            "l10n": "en",
            "filter": "none",
            "maxpassages": "1",
            "groupby": f"mode=flat.groups-on-page={self.count}",
        }

        result = self._open(url + urllib.parse.urlencode(params))

        try:
            data = lxml.etree.fromstring(result)
            return [elem.text for elem in data.xpath(".//url")]
        except lxml.etree.Error as exc:
            raise exceptions.SearchQueryError(f"Yandex XML parse error: {exc}")


SEARCH_ENGINES: dict[str, type[SearchEngine]] = {
    "Bing": BingSearchEngine,
    "Google": GoogleSearchEngine,
    "Yandex": YandexSearchEngine,
}


def get_search_engine(
    search_config: dict[str, Any], headers: list[tuple[str, str]]
) -> SearchEngine:
    """Return a function that can be called to do web searches.

    The function takes one argument, a search query, and returns a list of URLs, ranked
    by importance. The underlying logic depends on the *engine* argument within our
    config; for example, if *engine* is "Yahoo! BOSS", we'll use YahooBOSSSearchEngine
    for querying.

    Raises UnknownSearchEngineError if the 'engine' listed in our config is unknown to
    us, and UnsupportedSearchEngineError if we are missing a required package or
    module, like oauth2 for "Yahoo! BOSS".
    """
    engine = search_config["engine"]
    if engine not in SEARCH_ENGINES:
        raise exceptions.UnknownSearchEngineError(engine)

    klass = SEARCH_ENGINES[engine]
    credentials = search_config["credentials"]
    opener = urllib.request.build_opener()
    opener.addheaders = headers

    for dep in klass.requirements():
        try:
            __import__(dep).__name__
        except (ModuleNotFoundError, AttributeError):
            e = "Missing a required dependency ({}) for the {} engine"
            e = e.format(dep, engine)
            raise exceptions.UnsupportedSearchEngineError(e)

    return klass(credentials, opener)
