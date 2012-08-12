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

from os import path

import bs4
import mwparserfromhell
import nltk

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
        return "<{0} of text with size {1}>".format(name, len(self.text))


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
        clean = wikicode.strip_code(normalize=True, collapse=True)
        self.clean = clean.replace("\n\n", "\n")  # Collapse extra newlines
        return self.clean

    def chunk(self, nltk_dir, max_chunks, max_query=256):
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


class HTMLTextParser(BaseTextParser):
    """A parser that can extract the text from an HTML document."""
    hidden_tags = [
        "script", "style"
    ]

    def strip(self):
        """Return the actual text contained within an HTML document.

        Implemented using :py:mod:`BeautifulSoup <bs4>`
        (http://www.crummy.com/software/BeautifulSoup/).
        """
        try:
            soup = bs4.BeautifulSoup(self.text, "lxml").body
        except ValueError:
            soup = bs4.BeautifulSoup(self.text).body

        is_comment = lambda text: isinstance(text, bs4.element.Comment)
        [comment.extract() for comment in soup.find_all(text=is_comment)]
        for tag in self.hidden_tags:
            [element.extract() for element in soup.find_all(tag)]

        return "\n".join(soup.stripped_strings)
