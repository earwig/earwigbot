# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from os import path
import re
from StringIO import StringIO

import mwparserfromhell

from earwigbot import importer
from earwigbot.exceptions import ParserExclusionError

bs4 = importer.new("bs4")
nltk = importer.new("nltk")
converter = importer.new("pdfminer.converter")
pdfinterp = importer.new("pdfminer.pdfinterp")
pdfpage = importer.new("pdfminer.pdfpage")
pdftypes = importer.new("pdfminer.pdftypes")
psparser = importer.new("pdfminer.psparser")

__all__ = ["ArticleTextParser", "get_parser"]

class _BaseTextParser(object):
    """Base class for a parser that handles text."""
    TYPE = None

    def __init__(self, text, args=None):
        self.text = text
        self._args = args or {}

    def __repr__(self):
        """Return the canonical string representation of the text parser."""
        return "{0}(text={1!r})".format(self.__class__.__name__, self.text)

    def __str__(self):
        """Return a nice string representation of the text parser."""
        name = self.__class__.__name__
        return "<{0} of text with size {1}>".format(name, len(self.text))


class ArticleTextParser(_BaseTextParser):
    """A parser that can strip and chunk wikicode article text."""
    TYPE = "Article"
    TEMPLATE_MERGE_THRESHOLD = 35

    def _merge_templates(self, code):
        """Merge template contents in to wikicode when the values are long."""
        for template in code.filter_templates(recursive=code.RECURSE_OTHERS):
            chunks = []
            for param in template.params:
                if len(param.value) >= self.TEMPLATE_MERGE_THRESHOLD:
                    self._merge_templates(param.value)
                    chunks.append(param.value)
            if chunks:
                subst = u" ".join(map(unicode, chunks))
                code.replace(template, u" " + subst + u" ")
            else:
                code.remove(template)

    def strip(self):
        """Clean the page's raw text by removing templates and formatting.

        Return the page's text with all HTML and wikicode formatting removed,
        including templates, tables, and references. It retains punctuation
        (spacing, paragraphs, periods, commas, (semi)-colons, parentheses,
        quotes), original capitalization, and so forth. HTML entities are
        replaced by their unicode equivalents.

        The actual stripping is handled by :py:mod:`mwparserfromhell`.
        """
        def remove(code, node):
            """Remove a node from a code object, ignoring ValueError.

            Sometimes we will remove a node that contains another node we wish
            to remove, and we fail when we try to remove the inner one. Easiest
            solution is to just ignore the exception.
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
        self.clean = re.sub("\n\n+", "\n", clean).strip()
        return self.clean

    def chunk(self, nltk_dir, max_chunks, min_query=8, max_query=128):
        """Convert the clean article text into a list of web-searchable chunks.

        No greater than *max_chunks* will be returned. Each chunk will only be
        a sentence or two long at most (no more than *max_query*). The idea is
        to return a sample of the article text rather than the whole, so we'll
        pick and choose from parts of it, especially if the article is large
        and *max_chunks* is low, so we don't end up just searching for just the
        first paragraph.

        This is implemented using :py:mod:`nltk` (http://nltk.org/). A base
        directory (*nltk_dir*) is required to store nltk's punctuation
        database. This is typically located in the bot's working directory.
        """
        datafile = path.join(nltk_dir, "tokenizers", "punkt", "english.pickle")
        try:
            tokenizer = nltk.data.load("file:" + datafile)
        except LookupError:
            nltk.download("punkt", nltk_dir)
            tokenizer = nltk.data.load("file:" + datafile)

        sentences = []
        for sentence in tokenizer.tokenize(self.clean):
            if len(sentence) > max_query:
                words = sentence.split()
                while len(" ".join(words)) > max_query:
                    words.pop()
                sentence = " ".join(words)
            if len(sentence) < min_query:
                continue
            sentences.append(sentence)

        if max_chunks >= len(sentences):
            return sentences

        chunks = []
        while len(chunks) < max_chunks:
            if len(chunks) % 5 == 0:
                chunk = sentences.pop(0)  # Pop from beginning
            elif len(chunks) % 5 == 1:
                chunk = sentences.pop()  # Pop from end
            elif len(chunks) % 5 == 2:
                chunk = sentences.pop(len(sentences) / 2)  # Pop from Q2
            elif len(chunks) % 5 == 3:
                chunk = sentences.pop(len(sentences) / 4)  # Pop from Q1
            else:
                chunk = sentences.pop(3 * len(sentences) / 4)  # Pop from Q3
            chunks.append(chunk)
        return chunks

    def get_links(self):
        """Return a list of all external links in the article.

        The list is restricted to things that we suspect we can parse: i.e.,
        those with schemes of ``http`` and ``https``.
        """
        schemes = ("http://", "https://")
        links = mwparserfromhell.parse(self.text).ifilter_external_links()
        return [unicode(link.url) for link in links
                if link.url.startswith(schemes)]


class _HTMLParser(_BaseTextParser):
    """A parser that can extract the text from an HTML document."""
    TYPE = "HTML"
    hidden_tags = [
        "script", "style"
    ]

    def parse(self):
        """Return the actual text contained within an HTML document.

        Implemented using :py:mod:`BeautifulSoup <bs4>`
        (http://www.crummy.com/software/BeautifulSoup/).
        """
        try:
            soup = bs4.BeautifulSoup(self.text, "lxml")
        except ValueError:
            soup = bs4.BeautifulSoup(self.text)

        if not soup.body:
            # No <body> tag present in HTML ->
            # no scrapable content (possibly JS or <frame> magic):
            return ""

        if "mirror_hints" in self._args:
            # Look for obvious signs that this is a mirror:
            func = lambda attr: attr and any(
                hint in attr for hint in self._args["mirror_hints"])
            if soup.find_all(href=func) or soup.find_all(src=func):
                raise ParserExclusionError()

        soup = soup.body
        is_comment = lambda text: isinstance(text, bs4.element.Comment)
        for comment in soup.find_all(text=is_comment):
            comment.extract()
        for tag in self.hidden_tags:
            for element in soup.find_all(tag):
                element.extract()

        return "\n".join(soup.stripped_strings)


class _PDFParser(_BaseTextParser):
    """A parser that can extract text from a PDF file."""
    TYPE = "PDF"
    substitutions = [
        (u"\x0c", u"\n"),
        (u"\u2022", u" "),
    ]

    def parse(self):
        """Return extracted text from the PDF."""
        output = StringIO()
        manager = pdfinterp.PDFResourceManager()
        conv = converter.TextConverter(manager, output)
        interp = pdfinterp.PDFPageInterpreter(manager, conv)

        try:
            pages = pdfpage.PDFPage.get_pages(StringIO(self.text))
            for page in pages:
                interp.process_page(page)
        except (pdftypes.PDFException, psparser.PSException, AssertionError):
            return output.getvalue().decode("utf8")
        finally:
            conv.close()

        value = output.getvalue().decode("utf8")
        for orig, new in self.substitutions:
            value = value.replace(orig, new)
        return re.sub("\n\n+", "\n", value).strip()


class _PlainTextParser(_BaseTextParser):
    """A parser that can unicode-ify and strip text from a plain text page."""
    TYPE = "Text"

    def parse(self):
        """Unicode-ify and strip whitespace from the plain text document."""
        converted = bs4.UnicodeDammit(self.text).unicode_markup
        return converted.strip() if converted else ""


_CONTENT_TYPES = {
    "text/html": _HTMLParser,
    "application/xhtml+xml": _HTMLParser,
    "application/pdf": _PDFParser,
    "application/x-pdf": _PDFParser,
    "text/plain": _PlainTextParser
}

def get_parser(content_type):
    """Return the parser most able to handle a given content type, or None."""
    return _CONTENT_TYPES.get(content_type.split(";", 1)[0])
