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
        ``"Adding WikiProject banner {{BANNER}}."``
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
        r"skip ?to ?(toc|talk|toctalk)$",

        r"ga ?nominee$",

        r"(user ?)?talk ?(header|page|page ?header)$",

        r"community ?article ?probation$",
        r"censor(-nudity)?$",
        r"blp(o| ?others?)?$",
        r"controvers(ial2?|y)$",

        r"(not ?(a ?)?)?forum$",
        r"tv(episode|series)talk$",
        r"recurring ?themes$",
        r"faq$",
        r"(round ?in ?)?circ(les|ular)$",

        r"ar(ti|it)cle ?(history|milestones)$",
        r"failed ?ga$",
        r"old ?prod( ?full)?$",
        r"(old|previous) ?afd$",

        r"((wikiproject|wp) ?)?bio(graph(y|ies))?$",
    ]

    def _upperfirst(self, text):
        """Try to uppercase the first letter of a string."""
        try:
            return text[0].upper() + text[1:]
        except IndexError:
            return text

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

        site = self.bot.wiki.get_site(name=kwargs.get("site"))
        banner = kwargs["banner"]
        summary = kwargs.get("summary", "Adding WikiProject banner $3.")
        append = kwargs.get("append")
        autoassess = kwargs.get("autoassess", False)
        nocreate = kwargs.get("nocreate", False)
        recursive = kwargs.get("recursive", 0)
        banner, names = self.get_names(site, banner)
        if not names:
            return
        job = _Job(banner, names, summary, append, autoassess, nocreate)

        try:
            self.run_job(kwargs, site, job, recursive)
        except _ShutoffEnabled:
            return

    def run_job(self, kwargs, site, job, recursive):
        """Run a tagging *job* on a given *site*."""
        if "category" in kwargs:
            title = kwargs["category"]
            title = self.guess_namespace(site, title, constants.NS_CATEGORY)
            self.process_category(site.get_page(title), job, recursive)

        if "file" in kwargs:
            with open(kwargs["file"], "r") as fileobj:
                for line in fileobj:
                    if line.strip():
                        line = line.decode("utf8")
                        if line.startswith("[[") and line.endswith("]]"):
                            line = line[2:-2]
                        page = site.get_page(line)
                        if page.namespace == constants.NS_CATEGORY:
                            self.process_category(page, job, recursive)
                        else:
                            self.process_page(page, job)

    def guess_namespace(self, site, title, assumed):
        """If the given *title* does not have an explicit namespace, guess it.

        For example, when transcluding templates, the namespace is guessed to
        be ``NS_TEMPLATE`` unless one is explicitly declared (so ``{{foo}}`` ->
        ``[[Template:Foo]]``, but ``{{:foo}}`` -> ``[[Foo]]``).
        """
        prefix = title.split(":", 1)[0]
        if prefix == title:
            return u":".join((site.namespace_id_to_name(assumed), title))
        try:
            site.namespace_name_to_id(prefix)
        except exceptions.NamespaceNotFoundError:
            return u":".join((site.namespace_id_to_name(assumed), title))
        return title

    def get_names(self, site, banner):
        """Return all possible aliases for a given *banner* template."""
        title = self.guess_namespace(site, banner, constants.NS_TEMPLATE)
        if title == banner:
            banner = banner.split(":", 1)[1]
        page = site.get_page(title)
        if page.exists != page.PAGE_EXISTS:
            self.logger.error(u"Banner [[{0}]] does not exist".format(title))
            return banner, None

        if banner == title:
            names = [self._upperfirst(banner)]
        else:
            names = [self._upperfirst(banner), self._upperfirst(title)]
        result = site.api_query(action="query", list="backlinks", bllimit=500,
                                blfilterredir="redirects", bltitle=title)
        for backlink in result["query"]["backlinks"]:
            names.append(backlink["title"])
            if backlink["ns"] == constants.NS_TEMPLATE:
                names.append(backlink["title"].split(":", 1)[1])

        log = u"Found {0} aliases for banner [[{1}]]".format(len(names), title)
        self.logger.debug(log)
        return banner, names

    def process_category(self, page, job, recursive):
        """Try to tag all pages in the given category."""
        self.logger.info(u"Processing category: [[{0]]".format(page.title))
        for member in page.get_members():
            if member.namespace == constants.NS_CATEGORY:
                if recursive is True:
                    self.process_category(member, job, True)
                elif recursive:
                    self.process_category(member, job, recursive - 1)
            else:
                self.process_page(member, job)

    def process_page(self, page, job):
        """Try to tag a specific *page* using the *job* description."""
        if job.counter % 10 == 0:  # Do a shutoff check every ten pages
            if self.shutoff_enabled(page.site):
                raise _ShutoffEnabled()
        job.counter += 1

        if not page.is_talkpage:
            page = page.toggle_talk()
        try:
            code = page.parse()
        except exceptions.PageNotFoundError:
            if job.nocreate:
                log = u"Skipping nonexistent page: [[{0}]]".format(page.title)
                self.logger.info(log)
            else:
                log = u"Tagging new page: [[{0}]]".format(page.title)
                self.logger.info(log)
                banner = "{{" + job.banner + job.append + "}}"
                summary = job.summary.replace("$3", banner)
                page.edit(banner, self.make_summary(summary))
            return
        except exceptions.InvalidPageError:
            log = u"Skipping invalid page: [[{0}]]".format(page.title)
            self.logger.error(log)
            return

        for template in code.ifilter_templates(recursive=True):
            name = self._upperfirst(template.name.strip())
            if name in job.names:
                log = u"Skipping page: [[{0}]]; already tagged with '{1}'"
                self.logger.info(log.format(page.title, name))
                return

        banner = self.make_banner(job, code)
        shell = self.get_banner_shell(code)
        if shell:
            if shell.has_param(1):
                shell.get(1).value.insert(0, banner + "\n")
            else:
                shell.add(1, banner)
        else:
            self.add_banner(code, banner)
        self.apply_genfixes(code)

        self.logger.info(u"Tagging page: [[{0}]]".format(page.title))
        summary = job.summary.replace("$3", banner)
        page.edit(unicode(code), self.make_summary(summary))

    def make_banner(self, job, code):
        """Return banner text to add based on a *job* and a page's *code*."""
        banner = "{{" + job.banner
        if job.autoassess:
            classes = {"fa": 0, "fl": 0, "ga": 0, "a": 0, "b": 0, "start": 0,
                       "stub": 0, "list": 0, "dab": 0, "c": 0, "redirect": 0,
                       "book": 0, "template": 0, "category": 0}
            for template in code.ifilter_templates(recursive=True):
                if template.has_param("class"):
                    value = unicode(template.get("class").value).lower()
                    if value in classes:
                        classes[value] += 1
            values = tuple(classes.values())
            best = max(values)
            confidence = float(best) / sum(values)
            if confidence > 0.75:
                rank = tuple(classes.keys())[values.index(best)]
                if rank in ("fa", "fl", "ga"):
                    banner += "|class=" + rank.upper()
                else:
                    banner += "|class=" + self._upperfirst(rank)
        return banner + job.append + "}}"

    def get_banner_shell(self, code):
        """Return the banner shell template within *code*, else ``None``."""
        regex = r"^\{\{\s*((WikiProject|WP)[ _]?Banner[ _]?S(hell)?|W(BPS|PBS|PB)|Shell)"
        shells = code.filter_templates(matches=regex)
        if not shells:
            shells = code.filter_templates(matches=regex, recursive=True)
        if shells:
            log = u"Inserting banner into shell: {0}"
            self.logger.debug(log.format(shells[0].name))
            return shells[0]

    def add_banner(self, code, banner):
        """Add *banner* to *code*, following template order conventions."""
        index = 0
        for i, template in enumerate(code.ifilter_templates()):
            name = template.name.lower().replace("_", " ")
            for regex in self.TOP_TEMPS:
                if re.match(regex, name):
                    self.logger.info("Skipping top template: {0}".format(name))
                    index = i + 1

        self.logger.debug(u"Inserting banner at index {0}".format(index))
        code.insert(index, banner)

    def apply_genfixes(self, code):
        """Apply general fixes to *code*, such as template substitution."""
        regex = r"^\{\{\s*((un|no)?s(i((gn|ng)(ed3?)?|g))?|usu|tilde|forgot to sign|without signature)"
        for template in code.ifilter_templates(matches=regex):
            self.logger.debug("Applying genfix: substitute {{unsigned}}")
            template.name = "subst:unsigned"


class _Job(object):
    """Represents a single wikiproject-tagging task.

    Stores information on the banner to add, the edit summary to use, whether
    or not to autoassess and create new pages from scratch, and a counter of
    the number of pages edited.
    """
    def __init__(self, banner, names, summary, append, autoassess, nocreate):
        self.banner = banner
        self.names = names
        self.summary = summary
        self.append = append
        self.autoassess = autoassess
        self.nocreate = nocreate
        self.counter = 0


class _ShutoffEnabled(Exception):
    """Raised by process_page() if shutoff is enabled. Caught by run(), which
    will then stop the task."""
    pass
