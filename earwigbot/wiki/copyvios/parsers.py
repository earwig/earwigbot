# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

__all__ = ["BaseTextParser", "ArticleTextParser", "HTMLTextParser"]

class BaseTextParser(object):
    def __init__(self, text):
        self.text = text


class ArticleTextParser(BaseTextParser):
    def strip(self):
        """Clean the page's raw text by removing templates and formatting.

        Returns the page's text with all HTML and wikicode formatting removed,
        including templates, tables, references, and the Bibliography/
        References/Sources/See also section(s). It retains punctuation
        (spacing, paragraphs, periods, commas, (semi)-colons, parentheses,
        quotes) and original capitalization, but not brackets (square and
        angular), abnormal spacing, nor anything else. HTML entities are
        replaced by their unicode equivalents.

        The actual replacement is handled by a few private methods within this
        class.
        """
        text = self._strip_tags(self.text)
        text = self._strip_templates(text)
        text = self._strip_sections(text)
        text = self._strip_wikicode(text)
        text = self._normalize(text)
        return text

    def chunk(self, max_chunks):
        """Convert the article text into a list of web-searchable chunks.

        No greater than max_chunks will be returned. Each chunk will only be a
        couple sentences long at most. The idea here is to return a
        representative sample of the article text rather than the entire
        article, so we'll probably pick and choose from its introduction, body,
        and conclusion, especially if the article is large and max_chunks are
        few, so we don't end up just searching for the first paragraph.
        """
        return [self.text]

    def _strip_tags(self, text):
        return text

    def _strip_templates(self, text):
        return text

    def _strip_sections(self, text):
        return text

    def _strip_wikicode(self, text):
        return text

    def _normalize(self, text):
        return text


class HTMLTextParser(BaseTextParser):
    def strip(self):
        return self.text
