# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2019 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from hashlib import md5
from logging import getLogger, NullHandler
import re
from time import gmtime, strftime
from urllib import quote

import mwparserfromhell

from earwigbot import exceptions
from earwigbot.wiki.copyvios import CopyvioMixIn

__all__ = ["Page"]

class Page(CopyvioMixIn):
    """
    **EarwigBot: Wiki Toolset: Page**

    Represents a page on a given :py:class:`~earwigbot.wiki.site.Site`. Has
    methods for getting information about the page, getting page content, and
    so on. :py:class:`~earwigbot.wiki.category.Category` is a subclass of
    :py:class:`Page` with additional methods.

    *Attributes:*

    - :py:attr:`site`:        the page's corresponding Site object
    - :py:attr:`title`:       the page's title, or pagename
    - :py:attr:`exists`:      whether or not the page exists
    - :py:attr:`pageid`:      an integer ID representing the page
    - :py:attr:`url`:         the page's URL
    - :py:attr:`namespace`:   the page's namespace as an integer
    - :py:attr:`lastrevid`:   the ID of the page's most recent revision
    - :py:attr:`protection`:  the page's current protection status
    - :py:attr:`is_talkpage`: ``True`` if this is a talkpage, else ``False``
    - :py:attr:`is_redirect`: ``True`` if this is a redirect, else ``False``

    *Public methods:*

    - :py:meth:`reload`:      forcibly reloads the page's attributes
    - :py:meth:`toggle_talk`: returns a content page's talk page, or vice versa
    - :py:meth:`get`:         returns the page's content
    - :py:meth:`get_redirect_target`: returns the page's destination if it is a
      redirect
    - :py:meth:`get_creator`: returns a User object representing the first
      person to edit the page
    - :py:meth:`parse`:       parses the page content for templates, links, etc
    - :py:meth:`edit`:        replaces the page's content or creates a new page
    - :py:meth:`add_section`: adds a new section at the bottom of the page
    - :py:meth:`check_exclusion`: checks whether or not we are allowed to edit
      the page, per ``{{bots}}``/``{{nobots}}``

    - :py:meth:`~earwigbot.wiki.copyvios.CopyrightMixIn.copyvio_check`:
      checks the page for copyright violations
    - :py:meth:`~earwigbot.wiki.copyvios.CopyrightMixIn.copyvio_compare`:
      checks the page like :py:meth:`copyvio_check`, but against a specific URL
    """
    PAGE_UNKNOWN = 0
    PAGE_INVALID = 1
    PAGE_MISSING = 2
    PAGE_EXISTS = 3

    def __init__(self, site, title, follow_redirects=False, pageid=None,
                 logger=None):
        """Constructor for new Page instances.

        Takes four arguments: a Site object, the Page's title (or pagename),
        whether or not to follow redirects (optional, defaults to False), and
        a page ID to supplement the title (optional, defaults to None - i.e.,
        we will have to query the API to get it).

        As with User, site.get_page() is preferred.

        __init__() will not do any API queries, but it will use basic namespace
        logic to determine our namespace ID and if we are a talkpage.
        """
        super(Page, self).__init__(site)
        self._site = site
        self._title = title.strip()
        self._follow_redirects = self._keep_following = follow_redirects
        self._pageid = pageid

        # Set up our internal logger:
        if logger:
            self._logger = logger
        else:  # Just set up a null logger to eat up our messages:
            self._logger = getLogger("earwigbot.wiki")
            self._logger.addHandler(NullHandler())

        # Attributes to be loaded through the API:
        self._exists = self.PAGE_UNKNOWN
        self._is_redirect = None
        self._lastrevid = None
        self._protection = None
        self._fullurl = None
        self._content = None
        self._creator = None

        # Attributes used for editing/deleting/protecting/etc:
        self._basetimestamp = None
        self._starttimestamp = None

        # Try to determine the page's namespace using our site's namespace
        # converter:
        prefix = self._title.split(":", 1)[0]
        if prefix != title:  # ignore a page that's titled "Category" or "User"
            try:
                self._namespace = self.site.namespace_name_to_id(prefix)
            except exceptions.NamespaceNotFoundError:
                self._namespace = 0
        else:
            self._namespace = 0

        # Is this a talkpage? Talkpages have odd IDs, while content pages have
        # even IDs, excluding the "special" namespaces:
        if self._namespace < 0:
            self._is_talkpage = False
        else:
            self._is_talkpage = self._namespace % 2 == 1

    def __repr__(self):
        """Return the canonical string representation of the Page."""
        res = "Page(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Return a nice string representation of the Page."""
        return '<Page "{0}" of {1}>'.format(self.title, str(self.site))

    def _assert_validity(self):
        """Used to ensure that our page's title is valid.

        If this method is called when our page is not valid (and after
        _load_attributes() has been called), InvalidPageError will be raised.

        Note that validity != existence. If a page's title is invalid (e.g, it
        contains "[") it will always be invalid, and cannot be edited.
        """
        if self._exists == self.PAGE_INVALID:
            e = u"Page '{0}' is invalid.".format(self._title)
            raise exceptions.InvalidPageError(e)

    def _assert_existence(self):
        """Used to ensure that our page exists.

        If this method is called when our page doesn't exist (and after
        _load_attributes() has been called), PageNotFoundError will be raised.
        It will also call _assert_validity() beforehand.
        """
        self._assert_validity()
        if self._exists == self.PAGE_MISSING:
            e = u"Page '{0}' does not exist.".format(self._title)
            raise exceptions.PageNotFoundError(e)

    def _load(self):
        """Call _load_attributes() and follows redirects if we're supposed to.

        This method will only follow redirects if follow_redirects=True was
        passed to __init__() (perhaps indirectly passed by site.get_page()).
        It avoids the API's &redirects param in favor of manual following,
        so we can act more realistically (we don't follow double redirects, and
        circular redirects don't break us).

        This will raise RedirectError if we have a problem following, but that
        is a bug and should NOT happen.

        If we're following a redirect, this will make a grand total of three
        API queries. It's a lot, but each one is quite small.
        """
        self._load_attributes()

        if self._keep_following and self._is_redirect:
            self._title = self.get_redirect_target()
            self._keep_following = False  # don't follow double redirects
            self._content = None  # reset the content we just loaded
            self._load_attributes()

    def _load_attributes(self, result=None):
        """Load various data from the API in a single query.

        Loads self._title, ._exists, ._is_redirect, ._pageid, ._fullurl,
        ._protection, ._namespace, ._is_talkpage, ._creator, ._lastrevid, and
        ._starttimestamp using the API. It will do a query of its own unless
        *result* is provided, in which case we'll pretend *result* is what the
        query returned.

        Assuming the API is sound, this should not raise any exceptions.
        """
        if not result:
            query = self.site.api_query
            result = query(action="query", prop="info|revisions",
                           inprop="protection|url", rvprop="user", rvlimit=1,
                           rvdir="newer", titles=self._title)

        if "interwiki" in result["query"]:
            self._title = result["query"]["interwiki"][0]["title"]
            self._exists = self.PAGE_INVALID
            return

        res = result["query"]["pages"].values()[0]
        self._title = res["title"]  # Normalize our pagename/title
        self._is_redirect = "redirect" in res

        self._pageid = int(result["query"]["pages"].keys()[0])
        if self._pageid < 0:
            if "missing" in res:
                # If it has a negative ID and it's missing; we can still get
                # data like the namespace, protection, and URL:
                self._exists = self.PAGE_MISSING
            else:
                # If it has a negative ID and it's invalid, then break here,
                # because there's no other data for us to get:
                self._exists = self.PAGE_INVALID
                return
        else:
            self._exists = self.PAGE_EXISTS

        self._fullurl = res["fullurl"]
        self._protection = res["protection"]
        self._starttimestamp = strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())

        # We've determined the namespace and talkpage status in __init__()
        # based on the title, but now we can be sure:
        self._namespace = res["ns"]
        self._is_talkpage = self._namespace % 2 == 1  # talkpages have odd IDs

        # These last two fields will only be specified if the page exists:
        self._lastrevid = res.get("lastrevid")
        try:
            self._creator = res['revisions'][0]['user']
        except KeyError:
            pass

    def _load_content(self, result=None):
        """Load current page content from the API.

        If *result* is provided, we'll pretend that is the result of an API
        query and try to get content from that. Otherwise, we'll do an API
        query on our own.

        Don't call this directly, ever; use reload() followed by get() if you
        want to force content reloading.
        """
        if not result:
            query = self.site.api_query
            result = query(action="query", prop="revisions", rvlimit=1,
                           rvprop="content|timestamp", rvslots="main",
                           titles=self._title)

        res = result["query"]["pages"].values()[0]
        try:
            revision = res["revisions"][0]
            self._content = revision["slots"]["main"]["*"]
            self._basetimestamp = revision["timestamp"]
        except (KeyError, IndexError):
            # This can only happen if the page was deleted since we last called
            # self._load_attributes(). In that case, some of our attributes are
            # outdated, so force another self._load_attributes():
            self._load_attributes()
            self._assert_existence()

    def _edit(self, params=None, text=None, summary=None, minor=None, bot=None,
              force=None, section=None, captcha_id=None, captcha_word=None):
        """Edit the page!

        If *params* is given, we'll use it as our API query parameters.
        Otherwise, we'll build params using the given kwargs via
        _build_edit_params().

        We'll then try to do the API query, and catch any errors the API raises
        in _handle_edit_errors(). We'll then throw these back as subclasses of
        EditError.
        """
        # Weed out invalid pages before we get too far:
        self._assert_validity()

        # Build our API query string:
        if not params:
            params = self._build_edit_params(text, summary, minor, bot, force,
                                             section, captcha_id, captcha_word)
        else: # Make sure we have the right token:
            params["token"] = self.site.get_token()

        # Try the API query, catching most errors with our handler:
        try:
            result = self.site.api_query(**params)
        except exceptions.APIError as error:
            if not hasattr(error, "code"):
                raise  # We can only handle errors with a code attribute
            result = self._handle_edit_errors(error, params)

        # If everything was successful, reset invalidated attributes:
        if result["edit"]["result"] == "Success":
            self._content = None
            self._basetimestamp = None
            self._exists = self.PAGE_UNKNOWN
            return

        # Otherwise, there was some kind of problem. Throw an exception:
        raise exceptions.EditError(result["edit"])

    def _build_edit_params(self, text, summary, minor, bot, force, section,
                           captcha_id, captcha_word):
        """Given some keyword arguments, build an API edit query string."""
        unitxt = text.encode("utf8") if isinstance(text, unicode) else text
        hashed = md5(unitxt).hexdigest()  # Checksum to ensure text is correct
        params = {
            "action": "edit", "title": self._title, "text": text,
            "token": self.site.get_token(), "summary": summary, "md5": hashed}

        if section:
            params["section"] = section
        if captcha_id and captcha_word:
            params["captchaid"] = captcha_id
            params["captchaword"] = captcha_word
        if minor:
            params["minor"] = "true"
        else:
            params["notminor"] = "true"
        if bot:
            params["bot"] = "true"

        if not force:
            if self._starttimestamp:
                params["starttimestamp"] = self._starttimestamp
            if self._basetimestamp:
                params["basetimestamp"] = self._basetimestamp
            if self._exists == self.PAGE_MISSING:
                # Page does not exist; don't edit if it already exists:
                params["createonly"] = "true"
        else:
            params["recreate"] = "true"

        return params

    def _handle_edit_errors(self, error, params, retry=True):
        """If our edit fails due to some error, try to handle it.

        We'll either raise an appropriate exception (for example, if the page
        is protected), or we'll try to fix it (for example, if the token is
        invalid, we'll try to get a new one).
        """
        perms = ["noedit", "noedit-anon", "cantcreate", "cantcreate-anon",
                 "protectedtitle", "noimageredirect", "noimageredirect-anon",
                 "blocked"]
        if error.code in perms:
            raise exceptions.PermissionsError(error.info)
        elif error.code in ["editconflict", "pagedeleted", "articleexists"]:
            # These attributes are now invalidated:
            self._content = None
            self._basetimestamp = None
            self._exists = self.PAGE_UNKNOWN
            raise exceptions.EditConflictError(error.info)
        elif error.code == "badtoken" and retry:
            params["token"] = self.site.get_token(force=True)
            try:
                return self.site.api_query(**params)
            except exceptions.APIError as err:
                if not hasattr(err, "code"):
                    raise  # We can only handle errors with a code attribute
                return self._handle_edit_errors(err, params, retry=False)
        elif error.code in ["emptypage", "emptynewsection"]:
            raise exceptions.NoContentError(error.info)
        elif error.code == "contenttoobig":
            raise exceptions.ContentTooBigError(error.info)
        elif error.code == "spamdetected":
            raise exceptions.SpamDetectedError(error.info)
        elif error.code == "filtered":
            raise exceptions.FilteredError(error.info)
        raise exceptions.EditError(": ".join((error.code, error.info)))

    @property
    def site(self):
        """The page's corresponding Site object."""
        return self._site

    @property
    def title(self):
        """The page's title, or "pagename".

        This won't do any API queries on its own. Any other attributes or
        methods that do API queries will reload the title, however, like
        :py:attr:`exists` and :py:meth:`get`, potentially "normalizing" it or
        following redirects if :py:attr:`self._follow_redirects` is ``True``.
        """
        return self._title

    @property
    def exists(self):
        """Whether or not the page exists.

        This will be a number; its value does not matter, but it will equal
        one of :py:attr:`self.PAGE_INVALID <PAGE_INVALID>`,
        :py:attr:`self.PAGE_MISSING <PAGE_MISSING>`, or
        :py:attr:`self.PAGE_EXISTS <PAGE_EXISTS>`.

        Makes an API query only if we haven't already made one.
        """
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        return self._exists

    @property
    def pageid(self):
        """An integer ID representing the page.

        Makes an API query only if we haven't already made one and the *pageid*
        parameter to :py:meth:`__init__` was left as ``None``, which should be
        true for all cases except when pages are returned by an SQL generator
        (like :py:meth:`category.get_members()
        <earwigbot.wiki.category.Category.get_members>`).

        Raises :py:exc:`~earwigbot.exceptions.InvalidPageError` or
        :py:exc:`~earwigbot.exceptions.PageNotFoundError` if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._pageid:
            return self._pageid
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        self._assert_existence()  # Missing pages do not have IDs
        return self._pageid

    @property
    def url(self):
        """The page's URL.

        Like :py:meth:`title`, this won't do any API queries on its own. If the
        API was never queried for this page, we will attempt to determine the
        URL ourselves based on the title.
        """
        if self._fullurl:
            return self._fullurl
        else:
            encoded = self._title.encode("utf8").replace(" ", "_")
            slug = quote(encoded, safe="/:").decode("utf8")
            path = self.site._article_path.replace("$1", slug)
            return u"".join((self.site.url, path))

    @property
    def namespace(self):
        """The page's namespace ID (an integer).

        Like :py:meth:`title`, this won't do any API queries on its own. If the
        API was never queried for this page, we will attempt to determine the
        namespace ourselves based on the title.
        """
        return self._namespace

    @property
    def lastrevid(self):
        """The ID of the page's most recent revision.

        Raises :py:exc:`~earwigbot.exceptions.InvalidPageError` or
        :py:exc:`~earwigbot.exceptions.PageNotFoundError` if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        self._assert_existence()  # Missing pages don't have revisions
        return self._lastrevid

    @property
    def protection(self):
        """The page's current protection status.

        Makes an API query only if we haven't already made one.

        Raises :py:exc:`~earwigbot.exceptions.InvalidPageError` if the page
        name is invalid. Won't raise an error if the page is missing because
        those can still be create-protected.
        """
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        self._assert_validity()  # Invalid pages cannot be protected
        return self._protection

    @property
    def is_talkpage(self):
        """``True`` if the page is a talkpage, otherwise ``False``.

        Like :py:meth:`title`, this won't do any API queries on its own. If the
        API was never queried for this page, we will attempt to determine
        whether it is a talkpage ourselves based on its namespace.
        """
        return self._is_talkpage

    @property
    def is_redirect(self):
        """``True`` if the page is a redirect, otherwise ``False``.

        Makes an API query only if we haven't already made one.

        We will return ``False`` even if the page does not exist or is invalid.
        """
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        return self._is_redirect

    def reload(self):
        """Forcibly reload the page's attributes.

        Emphasis on *reload*: this is only necessary if there is reason to
        believe they have changed.
        """
        self._load()
        if self._content is not None:
            # Only reload content if it has already been loaded:
            self._load_content()

    def toggle_talk(self, follow_redirects=None):
        """Return a content page's talk page, or vice versa.

        The title of the new page is determined by namespace logic, not API
        queries. We won't make any API queries on our own.

        If *follow_redirects* is anything other than ``None`` (the default), it
        will be passed to the new :py:class:`~earwigbot.wiki.page.Page`
        object's :py:meth:`__init__`. Otherwise, we'll use the value passed to
        our own :py:meth:`__init__`.

        Will raise :py:exc:`~earwigbot.exceptions.InvalidPageError` if we try
        to get the talk page of a special page (in the ``Special:`` or
        ``Media:`` namespaces), but we won't raise an exception if our page is
        otherwise missing or invalid.
        """
        if self._namespace < 0:
            ns = self.site.namespace_id_to_name(self._namespace)
            e = u"Pages in the {0} namespace can't have talk pages.".format(ns)
            raise exceptions.InvalidPageError(e)

        if self._is_talkpage:
            new_ns = self._namespace - 1
        else:
            new_ns = self._namespace + 1

        if self._namespace != 0:
            body = self._title.split(":", 1)[1]
        else:
            body = self._title

        new_prefix = self.site.namespace_id_to_name(new_ns)

        # If the new page is in namespace 0, don't do ":Title" (it's correct,
        # but unnecessary), just do "Title":
        if new_prefix:
            new_title = u":".join((new_prefix, body))
        else:
            new_title = body

        if follow_redirects is None:
            follow_redirects = self._follow_redirects
        return Page(self.site, new_title, follow_redirects)

    def get(self):
        """Return page content, which is cached if you try to call get again.

        Raises InvalidPageError or PageNotFoundError if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._exists == self.PAGE_UNKNOWN:
            # Kill two birds with one stone by doing an API query for both our
            # attributes and our page content:
            query = self.site.api_query
            result = query(action="query", rvlimit=1, titles=self._title,
                           prop="info|revisions", inprop="protection|url",
                           rvprop="content|timestamp", rvslots="main")
            self._load_attributes(result=result)
            self._assert_existence()
            self._load_content(result=result)

            # Follow redirects if we're told to:
            if self._keep_following and self._is_redirect:
                self._title = self.get_redirect_target()
                self._keep_following = False  # Don't follow double redirects
                self._exists = self.PAGE_UNKNOWN  # Force another API query
                self.get()

            return self._content

        # Make sure we're dealing with a real page here. This may be outdated
        # if the page was deleted since we last called self._load_attributes(),
        # but self._load_content() can handle that:
        self._assert_existence()

        if self._content is None:
            self._load_content()

        return self._content

    def get_redirect_target(self):
        """If the page is a redirect, return its destination.

        Raises :py:exc:`~earwigbot.exceptions.InvalidPageError` or
        :py:exc:`~earwigbot.exceptions.PageNotFoundError` if the page name is
        invalid or the page does not exist, respectively. Raises
        :py:exc:`~earwigbot.exceptions.RedirectError` if the page is not a
        redirect.
        """
        re_redirect = r"^\s*\#\s*redirect\s*\[\[(.*?)\]\]"
        content = self.get()
        try:
            return re.findall(re_redirect, content, flags=re.I)[0]
        except IndexError:
            e = "The page does not appear to have a redirect target."
            raise exceptions.RedirectError(e)

    def get_creator(self):
        """Return the User object for the first person to edit the page.

        Makes an API query only if we haven't already made one. Normally, we
        can get the creator along with everything else (except content) in
        :py:meth:`_load_attributes`. However, due to a limitation in the API
        (can't get the editor of one revision and the content of another at
        both ends of the history), if our other attributes were only loaded
        through :py:meth:`get`, we'll have to do another API query.

        Raises :py:exc:`~earwigbot.exceptions.InvalidPageError` or
        :py:exc:`~earwigbot.exceptions.PageNotFoundError` if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._exists == self.PAGE_UNKNOWN:
            self._load()
        self._assert_existence()
        if not self._creator:
            self._load()
            self._assert_existence()
        return self.site.get_user(self._creator)

    def parse(self):
        """Parse the page content for templates, links, etc.

        Actual parsing is handled by :py:mod:`mwparserfromhell`. Raises
        :py:exc:`~earwigbot.exceptions.InvalidPageError` or
        :py:exc:`~earwigbot.exceptions.PageNotFoundError` if the page name is
        invalid or the page does not exist, respectively.
        """
        return mwparserfromhell.parse(self.get())

    def edit(self, text, summary, minor=False, bot=True, force=False):
        """Replace the page's content or creates a new page.

        *text* is the new page content, with *summary* as the edit summary.
        If *minor* is ``True``, the edit will be marked as minor. If *bot* is
        ``True``, the edit will be marked as a bot edit, but only if we
        actually have a bot flag.

        Use *force* to push the new content even if there's an edit conflict or
        the page was deleted/recreated between getting our edit token and
        editing our page. Be careful with this!
        """
        self._edit(text=text, summary=summary, minor=minor, bot=bot,
                   force=force)

    def add_section(self, text, title, minor=False, bot=True, force=False):
        """Add a new section to the bottom of the page.

        The arguments for this are the same as those for :py:meth:`edit`, but
        instead of providing a summary, you provide a section title. Likewise,
        raised exceptions are the same as :py:meth:`edit`'s.

        This should create the page if it does not already exist, with just the
        new section as content.
        """
        self._edit(text=text, summary=title, minor=minor, bot=bot, force=force,
                   section="new")

    def check_exclusion(self, username=None, optouts=None):
        """Check whether or not we are allowed to edit the page.

        Return ``True`` if we *are* allowed to edit this page, and ``False`` if
        we aren't.

        *username* is used to determine whether we are part of a specific list
        of allowed or disallowed bots (e.g. ``{{bots|allow=EarwigBot}}`` or
        ``{{bots|deny=FooBot,EarwigBot}}``). It's ``None`` by default, which
        will swipe our username from :py:meth:`site.get_user()
        <earwigbot.wiki.site.Site.get_user>`.\
        :py:attr:`~earwigbot.wiki.user.User.name`.

        *optouts* is a list of messages to consider this check as part of for
        the purpose of opt-out; it defaults to ``None``, which ignores the
        parameter completely. For example, if *optouts* is ``["nolicense"]``,
        we'll return ``False`` on ``{{bots|optout=nolicense}}`` or
        ``{{bots|optout=all}}``, but `True` on
        ``{{bots|optout=orfud,norationale,replaceable}}``.
        """
        def parse_param(template, param):
            value = template.get(param).value
            return [item.strip().lower() for item in value.split(",")]

        if not username:
            username = self.site.get_user().name

        # Lowercase everything:
        username = username.lower()
        optouts = [optout.lower() for optout in optouts] if optouts else []

        r_bots = r"\{\{\s*(no)?bots\s*(\||\}\})"
        filter = self.parse().ifilter_templates(recursive=True, matches=r_bots)
        for template in filter:
            if template.has_param("deny"):
                denies = parse_param(template, "deny")
                if "all" in denies or username in denies:
                    return False
            if template.has_param("allow"):
                allows = parse_param(template, "allow")
                if "all" in allows or username in allows:
                    continue
            if optouts and template.has_param("optout"):
                tasks = parse_param(template, "optout")
                matches = [optout in tasks for optout in optouts]
                if "all" in tasks or any(matches):
                    return False
            if template.name.strip().lower() == "nobots":
                return False

        return True
