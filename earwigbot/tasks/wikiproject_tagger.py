# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2017 Ben Kurtovic <ben.kurtovic@gmail.com>
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
    --banner BANNER (--category CAT | --file FILE) [--summary SUM] [--update]
    [--append PARAMS] [--autoassess [CLASSES]] [--only-with BANNER]
    [--nocreate] [--recursive [NUM]] [--site SITE] [--dry-run]`

    .. glossary::

    ``--banner BANNER``
        the page name of the banner to add, without a namespace (unless the
        namespace is something other than ``Template``) so
        ``--banner "WikiProject Biography"`` for ``{{WikiProject Biography}}``
    ``--category CAT`` or ``--file FILE``
        determines which pages to tag; either all pages in a category (to
        include subcategories as well, see ``--recursive``) or all
        pages/categories in a file (utf-8 encoded and path relative to the
        current directory)
    ``--summary SUM``
        an optional edit summary to use; defaults to
        ``"Tagging with WikiProject banner {{BANNER}}."``
    ``--update``
        updates existing banners with new fields; should include at least one
        of ``--append`` or ``--autoassess`` to be useful
    ``--append PARAMS``
        optional comma-separated parameters to append to the banner (after an
        auto-assessment, if any); use syntax ``importance=low,taskforce=yes``
        to add ``|importance=low|taskforce=yes``
    ``--autoassess [CLASSES]``
        try to assess each article's class automatically based on the class of
        other banners on the same page; if CLASSES is given as a
        comma-separated list, only those classes will be auto-assessed
    ``--only-with BANNER``
        only tag pages that already have the given banner
    ``--nocreate``
        don't create new talk pages with just a banner if the page doesn't
        already exist
    ``--recursive NUM``
        recursively go through subcategories up to a maximum depth of ``NUM``,
        or if ``NUM`` isn't provided, go infinitely (this can be dangerous)
    ``--tag-categories``
        also tag category pages
    ``--site SITE``
        the ID of the site to tag pages on, defaulting to the default site
    ``--dry-run``
        don't actually make any edits, just log the pages that would have been
        edited

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
    ]

    @staticmethod
    def _upperfirst(text):
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
        summary = kwargs.get("summary", "Tagging with WikiProject banner $3.")
        update = kwargs.get("update", False)
        append = kwargs.get("append")
        autoassess = kwargs.get("autoassess", False)
        ow_banner = kwargs.get("only-with")
        nocreate = kwargs.get("nocreate", False)
        recursive = kwargs.get("recursive", 0)
        tag_categories = kwargs.get("tag-categories", False)
        dry_run = kwargs.get("dry-run", False)
        banner, names = self.get_names(site, banner)
        if not names:
            return
        if ow_banner:
            _, only_with = self.get_names(site, ow_banner)
            if not only_with:
                return
        else:
            only_with = None

        job = _Job(banner=banner, names=names, summary=summary, update=update,
                   append=append, autoassess=autoassess, only_with=only_with,
                   nocreate=nocreate, tag_categories=tag_categories,
                   dry_run=dry_run)

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
            self.logger.error(u"Banner [[%s]] does not exist", title)
            return banner, None

        names = {banner, title}
        result = site.api_query(action="query", list="backlinks", bllimit=500,
                                blfilterredir="redirects", bltitle=title)
        for backlink in result["query"]["backlinks"]:
            names.add(backlink["title"])
            if backlink["ns"] == constants.NS_TEMPLATE:
                names.add(backlink["title"].split(":", 1)[1])

        log = u"Found %s aliases for banner [[%s]]"
        self.logger.debug(log, len(names), title)
        return banner, names

    def process_category(self, page, job, recursive):
        """Try to tag all pages in the given category."""
        if page.title in job.processed_cats:
            self.logger.debug(u"Skipping category, already processed: [[%s]]",
                              page.title)
            return
        self.logger.info(u"Processing category: [[%s]]", page.title)
        job.processed_cats.add(page.title)

        if job.tag_categories:
            self.process_page(page, job)
        for member in page.get_members():
            nspace = member.namespace
            if nspace == constants.NS_CATEGORY:
                if recursive is True:
                    self.process_category(member, job, True)
                elif recursive > 0:
                    self.process_category(member, job, recursive - 1)
                elif job.tag_categories:
                    self.process_page(member, job)
            elif nspace in (constants.NS_USER, constants.NS_USER_TALK):
                continue
            else:
                self.process_page(member, job)

    def process_page(self, page, job):
        """Try to tag a specific *page* using the *job* description."""
        if not page.is_talkpage:
            page = page.toggle_talk()

        if page.title in job.processed_pages:
            self.logger.debug(u"Skipping page, already processed: [[%s]]",
                              page.title)
            return
        job.processed_pages.add(page.title)

        if job.counter % 10 == 0:  # Do a shutoff check every ten pages
            if self.shutoff_enabled(page.site):
                raise _ShutoffEnabled()
        job.counter += 1

        try:
            code = page.parse()
        except exceptions.PageNotFoundError:
            self.process_new_page(page, job)
            return
        except exceptions.InvalidPageError:
            self.logger.error(u"Skipping invalid page: [[%s]]", page.title)
            return

        is_update = False
        for template in code.ifilter_templates(recursive=True):
            if template.name.matches(job.names):
                if job.update:
                    banner = template
                    is_update = True
                    break
                else:
                    log = u"Skipping page: [[%s]]; already tagged with '%s'"
                    self.logger.info(log, page.title, template.name)
                    return

        if job.only_with:
            if not any(template.name.matches(job.only_with)
                       for template in code.ifilter_templates(recursive=True)):
                log = u"Skipping page: [[%s]]; fails only-with condition"
                self.logger.info(log, page.title)
                return

        if is_update:
            old_banner = unicode(banner)
            self.update_banner(banner, job, code)
            if banner == old_banner:
                log = u"Skipping page: [[%s]]; already tagged and no updates"
                self.logger.info(log, page.title)
                return
            self.logger.info(u"Updating banner on page: [[%s]]", page.title)
            banner = banner.encode("utf8")
        else:
            self.logger.info(u"Tagging page: [[%s]]", page.title)
            banner = self.make_banner(job, code)
            shell = self.get_banner_shell(code)
            if shell:
                self.add_banner_to_shell(shell, banner)
            else:
                self.add_banner(code, banner)

        self.save_page(page, job, unicode(code), banner)

    def process_new_page(self, page, job):
        """Try to tag a *page* that doesn't exist yet using the *job*."""
        if job.nocreate or job.only_with:
            log = u"Skipping nonexistent page: [[%s]]"
            self.logger.info(log, page.title)
        else:
            self.logger.info(u"Tagging new page: [[%s]]", page.title)
            banner = self.make_banner(job)
            self.save_page(page, job, banner, banner)

    def save_page(self, page, job, text, banner):
        """Save a page with an updated banner."""
        if job.dry_run:
            self.logger.debug(u"[DRY RUN] Banner: %s", banner)
        else:
            summary = job.summary.replace("$3", banner)
            page.edit(text, self.make_summary(summary), minor=True)

    def make_banner(self, job, code=None):
        """Return banner text to add based on a *job* and a page's *code*."""
        banner = job.banner
        if code is not None and job.autoassess is not False:
            assess, reason = self.get_autoassessment(code, job.autoassess)
            if assess:
                banner += "|class=" + assess
                if reason:
                    banner += "|auto=" + reason
        if job.append:
            banner += "|" + "|".join(job.append.split(","))
        return "{{" + banner + "}}"

    def update_banner(self, banner, job, code):
        """Update an existing *banner* based on a *job* and a page's *code*."""
        has = lambda key: (banner.has(key) and
                           banner.get(key).value.strip() not in ("", "?"))

        if job.autoassess is not False:
            if not has("class"):
                assess, reason = self.get_autoassessment(code, job.autoassess)
                if assess:
                    banner.add("class", assess)
                    if reason:
                        banner.add("auto", reason)
        if job.append:
            for param in job.append.split(","):
                key, value = param.split("=", 1)
                if not has(key):
                    banner.add(key, value)

    def get_autoassessment(self, code, only_classes=None):
        """Get an autoassessment for a page.

        Return (assessed class as a string or None, assessment reason or None).
        """
        if only_classes is None or only_classes is True:
            classnames = ["a", "b", "book", "c", "dab", "fa", "fl", "ga",
                          "list", "redirect", "start", "stub"]
        else:
            classnames = [klass.strip().lower()
                          for klass in only_classes.split(",")]

        classes = {klass: 0 for klass in classnames}
        for template in code.ifilter_templates(recursive=True):
            if template.has("class"):
                value = unicode(template.get("class").value).lower()
                if value in classes:
                    classes[value] += 1

        values = tuple(classes.values())
        best = max(values)
        if best:
            confidence = float(best) / sum(values)
            if confidence > 0.75:
                rank = tuple(classes.keys())[values.index(best)]
                if rank in ("fa", "fl", "ga"):
                    return rank.upper(), "inherit"
                else:
                    return self._upperfirst(rank), "inherit"
        return None, None

    def get_banner_shell(self, code):
        """Return the banner shell template within *code*, else ``None``."""
        regex = r"^\{\{\s*((WikiProject|WP)[ _]?Banner[ _]?S(hell)?|W(BPS|PBS|PB)|Shell)\s*(\||\}\})"
        shells = code.filter_templates(matches=regex)
        if not shells:
            shells = code.filter_templates(matches=regex, recursive=True)
        if shells:
            log = u"Inserting banner into shell: %s"
            self.logger.debug(log, shells[0].name)
            return shells[0]

    def add_banner_to_shell(self, shell, banner):
        """Add *banner* to *shell*."""
        if shell.has_param(1):
            if unicode(shell.get(1).value).endswith("\n"):
                banner += "\n"
            else:
                banner = "\n" + banner
            shell.get(1).value.append(banner)
        else:
            shell.add(1, banner)

    def add_banner(self, code, banner):
        """Add *banner* to *code*, following template order conventions."""
        predecessor = None
        for template in code.ifilter_templates(recursive=False):
            name = template.name.lower().replace("_", " ")
            for regex in self.TOP_TEMPS:
                if re.match(regex, name):
                    self.logger.debug(u"Skipping past top template: %s", name)
                    predecessor = template
                    break
            if "wikiproject" in name or name.startswith("wp"):
                self.logger.debug(u"Skipping past banner template: %s", name)
                predecessor = template

        if predecessor:
            self.logger.debug("Inserting banner after template")
            if not unicode(predecessor).endswith("\n"):
                banner = "\n" + banner
            post = code.index(predecessor) + 1
            if len(code.nodes) > post and not code.get(post).startswith("\n"):
                banner += "\n"
            code.insert_after(predecessor, banner)
        else:
            self.logger.debug("Inserting banner at beginning")
            code.insert(0, banner + "\n")

class _Job(object):
    """Represents a single wikiproject-tagging task.

    Stores information on the banner to add, the edit summary to use, whether
    or not to autoassess and create new pages from scratch, and a counter of
    the number of pages edited.
    """
    def __init__(self, **kwargs):
        self.banner = kwargs["banner"]
        self.names = kwargs["names"]
        self.summary = kwargs["summary"]
        self.update = kwargs["update"]
        self.append = kwargs["append"]
        self.autoassess = kwargs["autoassess"]
        self.only_with = kwargs["only_with"]
        self.nocreate = kwargs["nocreate"]
        self.tag_categories = kwargs["tag_categories"]
        self.dry_run = kwargs["dry_run"]

        self.counter = 0
        self.processed_cats = set()
        self.processed_pages = set()


class _ShutoffEnabled(Exception):
    """Raised by process_page() if shutoff is enabled. Caught by run(), which
    will then stop the task."""
    pass
