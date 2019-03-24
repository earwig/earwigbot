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

from time import sleep, time
from urllib2 import build_opener

from earwigbot import exceptions
from earwigbot.wiki.copyvios.markov import MarkovChain
from earwigbot.wiki.copyvios.parsers import ArticleTextParser
from earwigbot.wiki.copyvios.search import SEARCH_ENGINES
from earwigbot.wiki.copyvios.workers import (
    globalize, localize, CopyvioWorkspace)

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
        self._addheaders = [("User-Agent", site.user_agent),
                            ("Accept-Encoding", "gzip")]

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
        if engine not in SEARCH_ENGINES:
            raise exceptions.UnknownSearchEngineError(engine)

        klass = SEARCH_ENGINES[engine]
        credentials = self._search_config["credentials"]
        opener = build_opener()
        opener.addheaders = self._addheaders

        for dep in klass.requirements():
            try:
                __import__(dep).__name__
            except (ImportError, AttributeError):
                e = "Missing a required dependency ({}) for the {} engine"
                e = e.format(dep, engine)
                raise exceptions.UnsupportedSearchEngineError(e)

        return klass(credentials, opener)

    def copyvio_check(self, min_confidence=0.75, max_queries=15, max_time=-1,
                      no_searches=False, no_links=False, short_circuit=True):
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

        Setting *no_searches* to ``True`` will cause only URLs in the wikitext
        of the page to be checked; no search engine queries will be made.
        Setting *no_links* to ``True`` will cause the opposite to happen: URLs
        in the wikitext will be ignored; search engine queries will be made
        only. Setting both of these to ``True`` is pointless.

        Normally, the checker will short-circuit if it finds a URL that meets
        *min_confidence*. This behavior normally causes it to skip any
        remaining URLs and web queries, but setting *short_circuit* to
        ``False`` will prevent this.

        Raises :exc:`.CopyvioCheckError` or subclasses
        (:exc:`.UnknownSearchEngineError`, :exc:`.SearchQueryError`, ...) on
        errors.
        """
        log = u"Starting copyvio check for [[{0}]]"
        self._logger.info(log.format(self.title))
        searcher = self._get_search_engine()
        parser = ArticleTextParser(self.get(), {
            "nltk_dir": self._search_config["nltk_dir"],
            "lang": self._site.lang
        })
        article = MarkovChain(parser.strip())
        parser_args = {}

        if self._exclusions_db:
            self._exclusions_db.sync(self.site.name)
            exclude = lambda u: self._exclusions_db.check(self.site.name, u)
            parser_args["mirror_hints"] = \
                self._exclusions_db.get_mirror_hints(self)
        else:
            exclude = None

        workspace = CopyvioWorkspace(
            article, min_confidence, max_time, self._logger, self._addheaders,
            short_circuit=short_circuit, parser_args=parser_args)

        if article.size < 20:  # Auto-fail very small articles
            result = workspace.get_result()
            self._logger.info(result.get_log_message(self.title))
            return result

        if not no_links:
            workspace.enqueue(parser.get_links(), exclude)
        num_queries = 0
        if not no_searches:
            chunks = parser.chunk(max_queries)
            for chunk in chunks:
                if short_circuit and workspace.finished:
                    workspace.possible_miss = True
                    break
                log = u"[[{0}]] -> querying {1} for {2!r}"
                self._logger.debug(log.format(self.title, searcher.name, chunk))
                workspace.enqueue(searcher.search(chunk), exclude)
                num_queries += 1
                sleep(1)

        workspace.wait()
        result = workspace.get_result(num_queries)
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
        article = MarkovChain(ArticleTextParser(self.get()).strip())
        workspace = CopyvioWorkspace(
            article, min_confidence, max_time, self._logger, self._addheaders,
            max_time, num_workers=1)
        workspace.enqueue([url])
        workspace.wait()
        result = workspace.get_result()
        self._logger.info(result.get_log_message(self.title))
        return result
