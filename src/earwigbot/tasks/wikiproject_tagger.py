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

import re
from dataclasses import dataclass, field
from typing import NotRequired, TypedDict, Unpack

from mwparserfromhell.nodes import Template
from mwparserfromhell.wikicode import Wikicode

from earwigbot import exceptions
from earwigbot.tasks import Task
from earwigbot.wiki import Category, Page, Site, constants

JobKwargs = TypedDict(
    "JobKwargs",
    {
        "banner": str,
        "category": NotRequired[str],
        "file": NotRequired[str],
        "summary": NotRequired[str],
        "update": NotRequired[bool],
        "append": NotRequired[str],
        "autoassess": NotRequired[bool | str],
        "only-with": NotRequired[str],
        "nocreate": NotRequired[bool],
        "recursive": NotRequired[bool | int],
        "tag-categories": NotRequired[bool],
        "not-in-category": NotRequired[str],
        "site": NotRequired[str],
        "dry-run": NotRequired[bool],
    },
)


@dataclass(frozen=True)
class Job:
    """
    Represents a single wikiproject-tagging task.

    Stores information on the banner to add, the edit summary to use, whether or not to
    autoassess and create new pages from scratch, and a counter of the number of pages
    edited.
    """

    banner: str
    names: set[str]
    summary: str
    update: bool
    append: str | None
    autoassess: bool | str
    only_with: set[str] | None
    nocreate: bool
    tag_categories: bool
    not_in_category: str | None
    dry_run: bool

    _counter: list[int] = [0]  # Wrap to allow frozen updates
    processed_cats: set[str] = field(default_factory=set)
    processed_pages: set[str] = field(default_factory=set)
    skip_pages: set[str] = field(default_factory=set)

    @property
    def counter(self) -> int:
        return self._counter[0]

    def add_to_counter(self, value: int) -> None:
        self._counter[0] += value


class ShutoffEnabled(Exception):
    """
    Raised by process_page() if shutoff is enabled.

    Caught by run(), which will then stop the task.
    """


class WikiProjectTagger(Task):
    """
    A task to tag talk pages with WikiProject banners.

    Usage: :command:`earwigbot -t wikiproject_tagger PATH --banner BANNER
    [--category CAT | --file FILE] [--summary SUM] [--update] [--append PARAMS]
    [--autoassess [CLASSES]] [--only-with BANNER] [--nocreate] [--recursive [NUM]]
    [--not-in-category CAT] [--site SITE] [--dry-run]`

    .. glossary::

    ``--banner BANNER``
        the page name of the banner to add, without a namespace (unless the namespace
        is something other than ``Template``) so ``--banner "WikiProject Biography"``
        for ``{{WikiProject Biography}}``
    ``--category CAT`` or ``--file FILE``
        determines which pages to tag; either all pages in a category (to include
        subcategories as well, see ``--recursive``) or all pages/categories in a file
        (utf-8 encoded and path relative to the current directory)
    ``--summary SUM``
        an optional edit summary to use; defaults to ``"Tagging with WikiProject banner
        {{BANNER}}."``
    ``--update``
        updates existing banners with new fields; should include at least one of
        ``--append`` or ``--autoassess`` to be useful
    ``--append PARAMS``
        optional comma-separated parameters to append to the banner (after an
        auto-assessment, if any); use syntax ``importance=low,taskforce=yes`` to add
        ``|importance=low|taskforce=yes``
    ``--autoassess [CLASSES]``
        try to assess each article's class automatically based on the class of other
        banners on the same page; if CLASSES is given as a comma-separated list, only
        those classes will be auto-assessed
    ``--only-with BANNER``
        only tag pages that already have the given banner
    ``--nocreate``
        don't create new talk pages with just a banner if the page doesn't
        already exist
    ``--recursive NUM``
        recursively go through subcategories up to a maximum depth of ``NUM``, or if
        ``NUM`` isn't provided, go infinitely (this can be dangerous)
    ``--tag-categories``
        also tag category pages
    ``--not-in-category CAT``
        skip talk pages that are already members of this category
    ``--site SITE``
        the ID of the site to tag pages on, defaulting to the default site
    ``--dry-run``
        don't actually make any edits, just log the pages that would have been edited
    """

    name = "wikiproject_tagger"

    # Regexes for template names that should always go above the banner, based on
    # [[Wikipedia:Talk page layout]]:
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
    def _upperfirst(text: str) -> str:
        """
        Try to uppercase the first letter of a string.
        """
        try:
            return text[0].upper() + text[1:]
        except IndexError:
            return text

    def run(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, **kwargs: Unpack[JobKwargs]
    ) -> None:
        """
        Main entry point for the bot task.
        """
        if "file" not in kwargs and "category" not in kwargs:
            self.logger.error(
                "No pages to tag; I need either a 'category' or a 'file' passed"
                "as kwargs"
            )
            return
        if "banner" not in kwargs:
            self.logger.error("Needs a banner to add passed as the 'banner' kwarg")
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
        not_in_category = kwargs.get("not-in-category")
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

        job = Job(
            banner=banner,
            names=names,
            summary=summary,
            update=update,
            append=append,
            autoassess=autoassess,
            only_with=only_with,
            nocreate=nocreate,
            tag_categories=tag_categories,
            not_in_category=not_in_category,
            dry_run=dry_run,
        )

        try:
            self.run_job(kwargs, site, job, recursive)
        except ShutoffEnabled:
            return

    def run_job(
        self, kwargs: JobKwargs, site: Site, job: Job, recursive: bool | int
    ) -> None:
        """
        Run a tagging *job* on a given *site*.
        """
        if job.not_in_category:
            skip_category = site.get_category(job.not_in_category)
            for page in skip_category.get_members():
                job.skip_pages.add(page.title)

        if "category" in kwargs:
            title = kwargs["category"]
            title = self.guess_namespace(site, title, constants.NS_CATEGORY)
            self.process_category(site.get_page(title), job, recursive)

        if "file" in kwargs:
            with open(kwargs["file"]) as fileobj:
                for line in fileobj:
                    if line.strip():
                        if "[[" in line:
                            match = re.search(r"\[\[(.+?)\]\]", line)
                            if match:
                                line = match.group(1)
                        page = site.get_page(line)
                        if page.namespace == constants.NS_CATEGORY:
                            self.process_category(page, job, recursive)
                        else:
                            self.process_page(page, job)

    def guess_namespace(self, site: Site, title: str, assumed: int) -> str:
        """
        If the given *title* does not have an explicit namespace, guess it.

        For example, when transcluding templates, the namespace is guessed to be
        ``NS_TEMPLATE`` unless one is explicitly declared (so ``{{foo}}`` ->
        ``[[Template:Foo]]``, but ``{{:foo}}`` -> ``[[Foo]]``).
        """
        prefix = title.split(":", 1)[0]
        if prefix == title:
            return ":".join((site.namespace_id_to_name(assumed), title))
        try:
            site.namespace_name_to_id(prefix)
        except exceptions.NamespaceNotFoundError:
            return ":".join((site.namespace_id_to_name(assumed), title))
        return title

    def get_names(self, site: Site, banner: str) -> tuple[str, set[str] | None]:
        """
        Return all possible aliases for a given *banner* template.
        """
        title = self.guess_namespace(site, banner, constants.NS_TEMPLATE)
        if title == banner:
            banner = banner.split(":", 1)[1]
        page = site.get_page(title)
        if page.exists != page.PAGE_EXISTS:
            self.logger.error(f"Banner [[{title}]] does not exist")
            return banner, None

        names = {banner, title}
        result = site.api_query(
            action="query",
            list="backlinks",
            bllimit=500,
            blfilterredir="redirects",
            bltitle=title,
        )
        for backlink in result["query"]["backlinks"]:
            names.add(backlink["title"])
            if backlink["ns"] == constants.NS_TEMPLATE:
                names.add(backlink["title"].split(":", 1)[1])

        self.logger.debug(f"Found {len(names)} aliases for banner [[{title}]]")
        return banner, names

    def process_category(self, page: Page, job: Job, recursive: bool | int) -> None:
        """
        Try to tag all pages in the given category.
        """
        assert isinstance(page, Category), f"[[{page.title}]] is not a category"
        if page.title in job.processed_cats:
            self.logger.debug(f"Skipping category, already processed: [[{page.title}]]")
            return
        self.logger.info(f"Processing category: [[{page.title}]]")
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

    def process_page(self, page: Page, job: Job) -> None:
        """
        Try to tag a specific *page* using the *job* description.
        """
        if not page.is_talkpage:
            page = page.toggle_talk()

        if page.title in job.skip_pages:
            self.logger.debug(f"Skipping page, in category to skip: [[{page.title}]]")
            return

        if page.title in job.processed_pages:
            self.logger.debug(f"Skipping page, already processed: [[{page.title}]]")
            return
        job.processed_pages.add(page.title)

        if job.counter % 10 == 0:  # Do a shutoff check every ten pages
            if self.shutoff_enabled(page.site):
                raise ShutoffEnabled()
        job.add_to_counter(1)

        try:
            code = page.parse()
        except exceptions.PageNotFoundError:
            self.process_new_page(page, job)
            return
        except exceptions.InvalidPageError:
            self.logger.error(f"Skipping invalid page: [[{page.title}]]")
            return

        banner = None
        is_update = False
        for template in code.ifilter_templates(recursive=True):
            if template.name.matches(job.names):
                if job.update:
                    banner = template
                    is_update = True
                    break
                else:
                    self.logger.info(
                        f"Skipping page: [[{page.title}]]; already tagged with "
                        f"{template.name!r}"
                    )
                    return

        if job.only_with:
            if not any(
                template.name.matches(job.only_with)
                for template in code.ifilter_templates(recursive=True)
            ):
                self.logger.info(
                    f"Skipping page: [[{page.title}]]; fails only-with condition"
                )
                return

        if is_update:
            assert banner is not None
            updated = self.update_banner(banner, job, code)
            if not updated:
                self.logger.info(
                    f"Skipping page: [[{page.title}]]; already tagged and no updates"
                )
                return
            self.logger.info(f"Updating banner on page: [[{page.title}]]")
            banner = str(banner)
        else:
            self.logger.info(f"Tagging page: [[{page.title}]]")
            banner = self.make_banner(job, code)
            shell = self.get_banner_shell(code)
            if shell:
                self.add_banner_to_shell(shell, banner)
            else:
                self.add_banner(code, banner)

        self.save_page(page, job, str(code), banner)

    def process_new_page(self, page: Page, job: Job) -> None:
        """
        Try to tag a *page* that doesn't exist yet using the *job*.
        """
        if job.nocreate or job.only_with:
            self.logger.info(f"Skipping nonexistent page: [[{page.title}]]")
        else:
            self.logger.info(f"Tagging new page: [[{page.title}]]")
            banner = self.make_banner(job)
            self.save_page(page, job, banner, banner)

    def save_page(self, page: Page, job: Job, text: str, banner: str) -> None:
        """
        Save a page with an updated banner.
        """
        if job.dry_run:
            self.logger.debug(f"[DRY RUN] Banner: {banner}")
        else:
            summary = job.summary.replace("$3", banner)
            page.edit(text, self.make_summary(summary), minor=True)

    def make_banner(self, job: Job, code: Wikicode | None = None) -> str:
        """
        Return banner text to add based on a *job* and a page's *code*.
        """
        banner = job.banner
        if code is not None and job.autoassess:
            assess, reason = self.get_autoassessment(code, job.autoassess)
            if assess:
                banner += "|class=" + assess
                if reason:
                    banner += "|auto=" + reason
        if job.append:
            banner += "|" + "|".join(job.append.split(","))
        return "{{" + banner + "}}"

    def update_banner(self, banner: Template, job: Job, code: Wikicode) -> bool:
        """
        Update an existing *banner* based on a *job* and a page's *code*.
        """

        def has(key: str) -> bool:
            return banner.has(key) and banner.get(key).value.strip() not in ("", "?")

        updated = False
        if job.autoassess:
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
                    updated = True
        return updated

    def get_autoassessment(
        self, code, only_classes: bool | str = False
    ) -> tuple[str, str] | tuple[None, None]:
        """
        Get an autoassessment for a page.

        Return (assessed class as a string or None, assessment reason or None).
        """
        if only_classes is None or only_classes is True:
            classnames = [
                "a",
                "b",
                "book",
                "c",
                "dab",
                "fa",
                "fl",
                "ga",
                "list",
                "redirect",
                "start",
                "stub",
            ]
        else:
            assert only_classes, only_classes
            classnames = [klass.strip().lower() for klass in only_classes.split(",")]

        classes = {klass: 0 for klass in classnames}
        for template in code.ifilter_templates(recursive=True):
            if template.has("class"):
                value = str(template.get("class").value).strip().lower()
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

    def get_banner_shell(self, code: Wikicode) -> Template | None:
        """
        Return the banner shell template within *code*, else ``None``.
        """
        regex = r"^\{\{\s*((WikiProject|WP)[ _]?Banner[ _]?S(hell)?|W(BPS|PBS|PB)|Shell)\s*(\||\}\})"
        shells = code.filter_templates(matches=regex)
        if not shells:
            shells = code.filter_templates(matches=regex, recursive=True)
        if shells:
            self.logger.debug(f"Inserting banner into shell: {shells[0].name}")
            return shells[0]

    def add_banner_to_shell(self, shell: Template, banner: str) -> None:
        """
        Add *banner* to *shell*.
        """
        if shell.has_param(1):
            if str(shell.get(1).value).endswith("\n"):
                banner += "\n"
            else:
                banner = "\n" + banner
            shell.get(1).value.append(banner)
        else:
            shell.add(1, banner)

    def add_banner(self, code: Wikicode, banner: str) -> None:
        """
        Add *banner* to *code*, following template order conventions.
        """
        predecessor = None
        for template in code.ifilter_templates(recursive=False):
            name = template.name.lower().replace("_", " ")
            for regex in self.TOP_TEMPS:
                if re.match(regex, name):
                    self.logger.debug(f"Skipping past top template: {name}")
                    predecessor = template
                    break
            if "wikiproject" in name or name.startswith("wp"):
                self.logger.debug(f"Skipping past banner template: {name}")
                predecessor = template

        if predecessor:
            self.logger.debug("Inserting banner after template")
            if not str(predecessor).endswith("\n"):
                banner = "\n" + banner
            post = code.index(predecessor) + 1
            if len(code.nodes) > post and not code.get(post).startswith("\n"):
                banner += "\n"
            code.insert_after(predecessor, banner)
        else:
            self.logger.debug("Inserting banner at beginning")
            code.insert(0, banner + "\n")
