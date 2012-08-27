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

import re

from earwigbot import exceptions
from earwigbot.tasks import Task
from earwigbot.wiki import constants

class WikiProjectTagger(Task):
    """A task to tag talk pages with WikiProject banners.

    Usage: :command:`earwigbot -t wikiproject_tagger PATH
    --banner BANNER (--category CAT | --file FILE) [--summary SUM]
    [--append TEXT] [--autoassess] [--nocreate] [--recursive NUM]
    [--site SITE]`

    .. glossary::

    ``--banner BANNER``
        the page name of the banner to add, without a namespace (unless the
        namespace is something other than ``Template``) so
        ``--banner WikiProject Biography`` for ``{{WikiProject Biography}}``
    ``--category CAT`` or ``--file FILE``
        determines which pages to tag; either all pages in a category (to
        include subcategories as well, see ``--recursive``) or all
        pages/categories in a file (utf-8 encoded and path relative to the
        current directory)
    ``--summary SUM``
        an optional edit summary to use; defaults to
        ``"Adding {{BANNER}} to article talk page."``
    ``--append TEXT``
        optional text to append to the banner (after an autoassessment, if
        any), like ``|importance=low``
    ``--autoassess``
        try to assess each article's class automatically based on the class of
        other banners on the same page
    ``--nocreate``
        don't create new talk pages with just a banner if the page doesn't
        already exist
    ``--recursive NUM``
        recursively go through subcategories up to a maximum depth of ``NUM``,
        or if ``NUM`` isn't provided, go infinitely (this can be dangerous)
    ``--site SITE``
        the ID of the site to tag pages on, defaulting to the... default site

    """
    name = "wikiproject_tagger"

    # Regexes for template names that should always go above the banner, based
    # on [[Wikipedia:Talk page layout]]:
    TOP_TEMPS = [
        "skip[ _]?to ?(toc|talk|toctalk)",

        "ga ?nominee",

        "(user ?)?talk ?(header|page|page ?header)",

        "community ?article ?probation",
        "censor(-nudity)?",
        "blp(o| ?others?)?",
        "controvers(ial2?|y)"

        "(not ?(a ?)?)?forum",
        "tv(episode|series)talk",
        "recurring ?themes",
        "faq",
        "(round ?in ?)?circ(les|ular)",

        "ar(ti|it)cle ?(history|milestones)",
        "failed ?ga",
        "old ?prod( ?full)?",
        "(old|previous) ?afd",

        "((wikiproject|wp) ?)?bio(graph(y|ies))?"
    ]

    def run(self, **kwargs):
        """Main entry point for the bot task."""
        if "file" not in kwargs and "category" not in kwargs:
            log = "No pages to tag; I need either a 'category' or a 'file' passed as kwargs"
            self.logger.error(log)
            return
        if "banner" not in kwargs:
            log = "Needs a banner to add passed as the 'banner' kwarg"
            self.logger.error(log)
            return

        banner = kwargs["banner"]
        summary = kwargs.get("summary", "Adding $3 to article talk page.")
        append = kwargs.get("append")
        autoassess = kwargs.get("autoassess", False)
        nocreate = kwargs.get("nocreate", False)
        recursive = kwargs.get("recursive", 0)
        site = self.bot.wiki.get_site(name=kwargs.get("site"))

        if "category" in kwargs:
            title = kwargs["category"]
            prefix = name.split(":", 1)[0]
            ns_cat = site.namespace_id_to_name(constants.NS_CATEGORY)
            if prefix == title:
                title = u":".join((ns_cat, title))
            else:
                try:
                    site.namespace_name_to_id(prefix)
                except exceptions.NamespaceNotFoundError:
                    title = u":".join((ns_cat, title))
            self.process_category(title, recursive)

        if "file" in kwargs:
            with open(kwargs["file"], "r") as fileobj:
                for line in fileobj:
                    if line.strip():
                        line = line.decode("utf8")
                        if line.startswith("[[") and line.endswith("]]"):
                            line = line[2:-2]
                        page = site.get_page(line)
                        if page.namespace == constants.NS_CATEGORY:
                            self.process_category(page, recursive)
                        else:
                            self.process_page(page)

    def process_category(self, page, recursive):
        for member in page.get_members():
            if member.namespace == constants.NS_CATEGORY:
                if recursive is True:
                    self.process_category(member, True)
                elif recursive:
                    self.process_category(member, recursive - 1)
            else:
                self.process_page(member)

    def process_page(self, page):
        raise NotImplementedError(page)
