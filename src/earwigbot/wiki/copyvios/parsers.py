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

from __future__ import annotations

__all__ = ["ArticleParser", "get_parser"]

import io
import json
import os.path
import re
import typing
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar, Literal, TypedDict

import mwparserfromhell

from earwigbot.exceptions import ParserExclusionError, ParserRedirectError

if typing.TYPE_CHECKING:
    import bs4

    from earwigbot.wiki.copyvios.workers import OpenedURL


class ArticleParser:
    """A parser that can strip and chunk wikicode article text."""

    TEMPLATE_MERGE_THRESHOLD = 35
    NLTK_DEFAULT = "english"
    NLTK_LANGS = {
        "cs": "czech",
        "da": "danish",
        "de": "german",
        "el": "greek",
        "en": "english",
        "es": "spanish",
        "et": "estonian",
        "fi": "finnish",
        "fr": "french",
        "it": "italian",
        "nl": "dutch",
        "no": "norwegian",
        "pl": "polish",
        "pt": "portuguese",
        "sl": "slovene",
        "sv": "swedish",
        "tr": "turkish",
    }

    def __init__(self, text: str, lang: str, nltk_dir: str) -> None:
        self.text = text
        self._lang = lang
        self._nltk_dir = nltk_dir

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(text={self.text!r})"

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} of text with size {len(self.text)}>"

    def _merge_templates(self, code: mwparserfromhell.wikicode.Wikicode) -> None:
        """Merge template contents in to wikicode when the values are long."""
        for template in code.filter_templates(recursive=code.RECURSE_OTHERS):
            chunks = []
            for param in template.params:
                if len(param.value) >= self.TEMPLATE_MERGE_THRESHOLD:
                    self._merge_templates(param.value)
                    chunks.append(param.value)
            if chunks:
                subst = " ".join(map(str, chunks))
                code.replace(template, " " + subst + " ")
            else:
                code.remove(template)

    def _get_tokenizer(self) -> Any:
        """Return a NLTK punctuation tokenizer for the article's language."""
        import nltk

        def datafile(lang: str) -> str:
            return "file:" + os.path.join(
                self._nltk_dir, "tokenizers", "punkt", lang + ".pickle"
            )

        lang = self.NLTK_LANGS.get(self._lang, self.NLTK_DEFAULT)
        try:
            nltk.data.load(datafile(self.NLTK_DEFAULT))
        except LookupError:
            nltk.download("punkt", self._nltk_dir)
        return nltk.data.load(datafile(lang))

    def _get_sentences(
        self, min_query: int, max_query: int, split_thresh: int
    ) -> list[str]:
        """Split the article text into sentences of a certain length."""

        def cut_sentence(words):
            div = len(words)
            if div == 0:
                return []

            length = len(" ".join(words))
            while length > max_query:
                div -= 1
                length -= len(words[div]) + 1

            result = []
            if length >= split_thresh:
                result.append(" ".join(words[:div]))
            return result + cut_sentence(words[div + 1 :])

        tokenizer = self._get_tokenizer()
        sentences = []
        if not hasattr(self, "clean"):
            self.strip()

        for sentence in tokenizer.tokenize(self.clean):
            if len(sentence) <= max_query:
                sentences.append(sentence)
            else:
                sentences.extend(cut_sentence(sentence.split()))
        return [sen for sen in sentences if len(sen) >= min_query]

    def strip(self) -> str:
        """
        Clean the page's raw text by removing templates and formatting.

        Return the page's text with all HTML and wikicode formatting removed, including
        templates, tables, and references. It retains punctuation (spacing, paragraphs,
        periods, commas, (semi)-colons, parentheses, quotes), original capitalization,
        and so forth. HTML entities are replaced by their unicode equivalents.

        The actual stripping is handled by :py:mod:`mwparserfromhell`.
        """

        def remove(
            code: mwparserfromhell.wikicode.Wikicode, node: mwparserfromhell.nodes.Node
        ) -> None:
            """
            Remove a node from a code object, ignoring ValueError.

            Sometimes we will remove a node that contains another node we wish to
            remove, and we fail when we try to remove the inner one. Easiest solution
            is to just ignore the exception.
            """
            try:
                code.remove(node)
            except ValueError:
                pass

        wikicode = mwparserfromhell.parse(self.text)

        # Preemtively strip some links mwparser doesn't know about:
        bad_prefixes = ("file:", "image:", "category:")
        for link in wikicode.filter_wikilinks():
            if link.title.strip().lower().startswith(bad_prefixes):
                remove(wikicode, link)

        # Also strip references:
        for tag in wikicode.filter_tags(matches=lambda tag: tag.tag == "ref"):
            remove(wikicode, tag)

        # Merge in template contents when the values are long:
        self._merge_templates(wikicode)

        clean = wikicode.strip_code(normalize=True, collapse=True)
        self.clean = re.sub(r"\n\n+", "\n", clean).strip()
        return self.clean

    def chunk(
        self,
        max_chunks: int,
        min_query: int = 8,
        max_query: int = 128,
        split_thresh: int = 32,
    ) -> list[str]:
        """
        Convert the clean article text into a list of web-searchable chunks.

        No greater than *max_chunks* will be returned. Each chunk will only be a
        sentence or two long at most (no more than *max_query*). The idea is to return
        a sample of the article text rather than the whole, so we'll pick and choose
        from parts of it, especially if the article is large and *max_chunks* is low,
        so we don't end up just searching for just the first paragraph.

        This is implemented using :py:mod:`nltk` (https://nltk.org/). A base directory
        (*nltk_dir*) is required to store nltk's punctuation database, and should be
        passed as an argument to the constructor. It is typically located in the bot's
        working directory.
        """
        sentences = self._get_sentences(min_query, max_query, split_thresh)
        if len(sentences) <= max_chunks:
            return sentences

        chunks: list[str] = []
        while len(chunks) < max_chunks:
            if len(chunks) % 5 == 0:
                chunk = sentences.pop(0)  # Pop from beginning
            elif len(chunks) % 5 == 1:
                chunk = sentences.pop()  # Pop from end
            elif len(chunks) % 5 == 2:
                chunk = sentences.pop(len(sentences) // 2)  # Pop from Q2
            elif len(chunks) % 5 == 3:
                chunk = sentences.pop(len(sentences) // 4)  # Pop from Q1
            else:
                chunk = sentences.pop(3 * len(sentences) // 4)  # Pop from Q3
            chunks.append(chunk)
        return chunks

    def get_links(self):
        """
        Return a list of all external links in the article.

        The list is restricted to things that we suspect we can parse: i.e.,
        those with schemes of ``http`` and ``https``.
        """
        schemes = ("http://", "https://")
        links = mwparserfromhell.parse(self.text).ifilter_external_links()
        return [str(link.url) for link in links if link.url.startswith(schemes)]


class ParserArgs(TypedDict, total=False):
    mirror_hints: list[str]
    open_url: Callable[[str], OpenedURL | None]


class SourceParser(ABC):
    """Base class for a parser that handles text."""

    TYPE: ClassVar[str]

    def __init__(self, text: bytes, url: str, args: ParserArgs | None = None) -> None:
        self.text = text
        self.url = url
        self._args = args or {}

    def __repr__(self) -> str:
        """Return the canonical string representation of the text parser."""
        return f"{self.__class__.__name__}(text={self.text!r})"

    def __str__(self) -> str:
        """Return a nice string representation of the text parser."""
        return f"<{self.__class__.__name__} of text with size {len(self.text)}>"

    @abstractmethod
    def parse(self) -> str: ...


class HTMLParser(SourceParser):
    """A parser that can extract the text from an HTML document."""

    TYPE = "HTML"
    hidden_tags = ["script", "style"]

    def _fail_if_mirror(self, soup: bs4.BeautifulSoup) -> None:
        """
        Look for obvious signs that the given soup is a wiki mirror.

        If so, raise ParserExclusionError, which is caught in the workers and
        causes this source to excluded.
        """
        if "mirror_hints" not in self._args:
            return

        def func(attr):
            assert "mirror_hints" in self._args
            return attr and any(hint in attr for hint in self._args["mirror_hints"])

        if soup.find_all(href=func) or soup.find_all(src=func):
            raise ParserExclusionError()

    @staticmethod
    def _get_soup(text: bytes) -> bs4.BeautifulSoup:
        """Parse some text using BeautifulSoup."""
        import bs4

        try:
            return bs4.BeautifulSoup(text, "lxml")
        except ValueError:
            return bs4.BeautifulSoup(text)

    def _clean_soup(self, soup: bs4.element.Tag) -> str:
        """Clean a BeautifulSoup tree of invisible tags."""
        import bs4

        def is_comment(text: bs4.element.Tag) -> bool:
            return isinstance(text, bs4.element.Comment)

        for comment in soup.find_all(text=is_comment):
            comment.extract()
        for tag in self.hidden_tags:
            for element in soup.find_all(tag):
                element.extract()

        return "\n".join(s.replace("\n", " ") for s in soup.stripped_strings)

    def _open(self, url: str, **kwargs: Any) -> bytes | None:
        """Try to read a URL. Return None if it couldn't be read."""
        opener = self._args.get("open_url")
        if not opener:
            return None
        result = opener(url, **kwargs)
        return result.content if result else None

    def _load_from_blogspot(self, url: urllib.parse.ParseResult) -> str:
        """Load dynamic content from Blogger Dynamic Views."""
        match = re.search(rb"'postId': '(\d+)'", self.text)
        if not match:
            return ""
        post_id = match.group(1)
        feed_url = f"https://{url.netloc}/feeds/posts/default/{post_id}?"
        params = {
            "alt": "json",
            "v": "2",
            "dynamicviews": "1",
            "rewriteforssl": "true",
        }
        raw = self._open(
            feed_url + urllib.parse.urlencode(params),
            allow_content_types=["application/json"],
        )
        if raw is None:
            return ""
        try:
            parsed = json.loads(raw)
        except ValueError:
            return ""
        try:
            text = parsed["entry"]["content"]["$t"]
        except KeyError:
            return ""
        soup = self._get_soup(text)
        if not soup.body:
            return ""
        return self._clean_soup(soup.body)

    def parse(self) -> str:
        """
        Return the actual text contained within an HTML document.

        Implemented using :py:mod:`BeautifulSoup <bs4>`
        (https://pypi.org/project/beautifulsoup4/).
        """
        import bs4

        url = urllib.parse.urlparse(self.url) if self.url else None
        soup = self._get_soup(self.text)
        if not soup.body:
            # No <body> tag present in HTML -> # no scrapable content
            # (possibly JS or <iframe> magic):
            return ""

        self._fail_if_mirror(soup)
        body = soup.body

        if url and url.netloc == "web.archive.org" and url.path.endswith(".pdf"):
            playback = body.find(id="playback")
            if isinstance(playback, bs4.element.Tag) and "src" in playback.attrs:
                raise ParserRedirectError(playback.attrs["src"])

        content = self._clean_soup(body)

        if url and url.netloc.endswith(".blogspot.com") and not content:
            content = self._load_from_blogspot(url)

        return content


class PDFParser(SourceParser):
    """A parser that can extract text from a PDF file."""

    TYPE = "PDF"
    substitutions = [
        ("\x0c", "\n"),
        ("\u2022", " "),
    ]

    def parse(self) -> str:
        """Return extracted text from the PDF."""
        from pdfminer import converter, pdfinterp, pdfpage

        output = io.StringIO()
        manager = pdfinterp.PDFResourceManager()
        conv = converter.TextConverter(manager, output)
        interp = pdfinterp.PDFPageInterpreter(manager, conv)

        try:
            pages = pdfpage.PDFPage.get_pages(io.BytesIO(self.text))
            for page in pages:
                interp.process_page(page)
        except Exception:  # pylint: disable=broad-except
            return output.getvalue()
        finally:
            conv.close()

        value = output.getvalue()
        for orig, new in self.substitutions:
            value = value.replace(orig, new)
        return re.sub(r"\n\n+", "\n", value).strip()


class PlainTextParser(SourceParser):
    """A parser that can unicode-ify and strip text from a plain text page."""

    TYPE = "Text"

    def parse(self) -> str:
        """Unicode-ify and strip whitespace from the plain text document."""
        from bs4.dammit import UnicodeDammit

        converted = UnicodeDammit(self.text).unicode_markup
        return converted.strip() if converted else ""


_CONTENT_TYPES: dict[str, type[SourceParser]] = {
    "text/html": HTMLParser,
    "application/xhtml+xml": HTMLParser,
    "application/pdf": PDFParser,
    "application/x-pdf": PDFParser,
    "text/plain": PlainTextParser,
}


@typing.overload
def get_parser(content_type: str) -> type[SourceParser] | None: ...


@typing.overload
def get_parser(
    content_type: Literal["text/plain"] = "text/plain",
) -> type[SourceParser]: ...


def get_parser(content_type: str = "text/plain") -> type[SourceParser] | None:
    """Return the parser most able to handle a given content type, or None."""
    return _CONTENT_TYPES.get(content_type)
