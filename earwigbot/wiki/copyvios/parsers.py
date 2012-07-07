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

try:
    import mwparserfromhell
except ImportError:
    mwparserfromhell = None

__all__ = ["BaseTextParser", "ArticleTextParser", "HTMLTextParser"]

class BaseTextParser(object):
    """Base class for a parser that handles text."""

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        """Return the canonical string representation of the text parser."""
        return "{0}(text={1!r})".format(self.__class__.__name__, self.text)

    def __str__(self):
        """Return a nice string representation of the text parser."""
        name = self.__class__.__name__
        return "<{0} of text with size {1}>".format(name, len(text))


class ArticleTextParser(BaseTextParser):
    """A parser that can strip and chunk wikicode article text."""

    def strip(self):
        """Clean the page's raw text by removing templates and formatting.

        Return the page's text with all HTML and wikicode formatting removed,
        including templates, tables, and references. It retains punctuation
        (spacing, paragraphs, periods, commas, (semi)-colons, parentheses,
        quotes), original capitalization, and so forth. HTML entities are
        replaced by their unicode equivalents.

        The actual stripping is handled by :py:mod:`mwparserfromhell`.
        """
        wikicode = mwparserfromhell.parse(self.text)
        self.clean = u" ".join(wikicode.normalize().ifilter_text())
        return self.clean

    def chunk(self, max_chunks):
        """Convert the clean article text into a list of web-searchable chunks.

        No greater than *max_chunks* will be returned. Each chunk will only be
        a couple sentences long at most. The idea here is to return a
        representative sample of the article text rather than the entire
        article, so we'll probably pick and choose from its introduction, body,
        and conclusion, especially if the article is large and *max_chunks* is
        low, so we don't end up just searching for the first paragraph.
        """
        return [self.text]                                                                          # TODO: NotImplemented


class HTMLTextParser(BaseTextParser):
    """A parser that can extract the text from an HTML document."""

    def strip(self):
        return self.text                                                                            # TODO: NotImplemented
