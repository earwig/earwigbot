# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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
import re
from time import gmtime, strftime
from urllib import quote

from earwigbot.wiki.exceptions import *

class Page(object):
    """
    EarwigBot's Wiki Toolset: Page Class

    Represents a Page on a given Site. Has methods for getting information
    about the page, getting page content, and so on. Category is a subclass of
    Page with additional methods.

    Public methods:
    title               -- returns the page's title, or pagename
    exists              -- returns whether the page exists
    pageid              -- returns an integer ID representing the page
    url                 -- returns the page's URL
    namespace           -- returns the page's namespace as an integer
    protection          -- returns the page's current protection status
    creator             -- returns the page's creator (first user to edit)
    is_talkpage         -- returns True if the page is a talkpage, else False
    is_redirect         -- returns True if the page is a redirect, else False
    toggle_talk         -- returns a content page's talk page, or vice versa
    get                 -- returns page content
    get_redirect_target -- if the page is a redirect, returns its destination
    edit                -- replaces the page's content or creates a new page
    add_section         -- add a new section at the bottom of the page
    """

    re_redirect = "^\s*\#\s*redirect\s*\[\[(.*?)\]\]"

    def __init__(self, site, title, follow_redirects=False):
        """Constructor for new Page instances.

        Takes three arguments: a Site object, the Page's title (or pagename),
        and whether or not to follow redirects (optional, defaults to False).

        As with User, site.get_page() is preferred. Site's method has support
        for a default `follow_redirects` value in our config, while __init__
        always defaults to False.

        __init__ will not do any API queries, but it will use basic namespace
        logic to determine our namespace ID and if we are a talkpage.
        """
        self._site = site
        self._title = title.strip()
        self._follow_redirects = self._keep_following = follow_redirects

        self._exists = 0
        self._pageid = None
        self._is_redirect = None
        self._lastrevid = None
        self._protection = None
        self._fullurl = None
        self._content = None
        self._creator = None

        # Attributes used for editing/deleting/protecting/etc:
        self._token = None
        self._basetimestamp = None
        self._starttimestamp = None

        # Try to determine the page's namespace using our site's namespace
        # converter:
        prefix = self._title.split(":", 1)[0]
        if prefix != title:  # ignore a page that's titled "Category" or "User"
            try:
                self._namespace = self._site.namespace_name_to_id(prefix)
            except NamespaceNotFoundError:
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
        """Returns the canonical string representation of the Page."""
        res = "Page(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Returns a nice string representation of the Page."""
        return '<Page "{0}" of {1}>'.format(self.title(), str(self._site))

    def _force_validity(self):
        """Used to ensure that our page's title is valid.

        If this method is called when our page is not valid (and after
        _load_attributes() has been called), InvalidPageError will be raised.

        Note that validity != existence. If a page's title is invalid (e.g, it
        contains "[") it will always be invalid, and cannot be edited.
        """
        if self._exists == 1:
            e = "Page '{0}' is invalid.".format(self._title)
            raise InvalidPageError(e)

    def _force_existence(self):
        """Used to ensure that our page exists.

        If this method is called when our page doesn't exist (and after
        _load_attributes() has been called), PageNotFoundError will be raised.
        It will also call _force_validity() beforehand.
        """
        self._force_validity()
        if self._exists == 2:
            e = "Page '{0}' does not exist.".format(self._title)
            raise PageNotFoundError(e)

    def _load_wrapper(self):
        """Calls _load_attributes() and follows redirects if we're supposed to.

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
        """Loads various data from the API in a single query.

        Loads self._title, ._exists, ._is_redirect, ._pageid, ._fullurl,
        ._protection, ._namespace, ._is_talkpage, ._creator, ._lastrevid,
        ._token, and ._starttimestamp using the API. It will do a query of
        its own unless `result` is provided, in which case we'll pretend
        `result` is what the query returned.

        Assuming the API is sound, this should not raise any exceptions.
        """
        if result is None:
            params = {"action": "query", "rvprop": "user", "intoken": "edit",
                      "prop": "info|revisions", "rvlimit": 1, "rvdir": "newer",
                      "titles": self._title, "inprop": "protection|url"}
            result = self._site._api_query(params)

        res = result["query"]["pages"].values()[0]

        # Normalize our pagename/title thing:
        self._title = res["title"]

        try:
            res["redirect"]
        except KeyError:
            self._is_redirect = False
        else:
            self._is_redirect = True

        self._pageid = result["query"]["pages"].keys()[0]
        if int(self._pageid) < 0:
            try:
                res["missing"]
            except KeyError:
                # If it has a negative ID and it's invalid, then break here,
                # because there's no other data for us to get:
                self._exists = 1
                return
            else:
                # If it has a negative ID and it's missing; we can still get
                # data like the namespace, protection, and URL:
                self._exists = 2
        else:
            self._exists = 3

        self._fullurl = res["fullurl"]
        self._protection = res["protection"]

        try:
            self._token = res["edittoken"]
        except KeyError:
            pass
        else:
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
        """Loads current page content from the API.

        If `result` is provided, we'll pretend that is the result of an API
        query and try to get content from that. Otherwise, we'll do an API
        query on our own.

        Don't call this directly, ever - use .get(force=True) if you want to
        force content reloading.
        """
        if result is None:
            params = {"action": "query", "prop": "revisions", "rvlimit": 1,
                      "rvprop": "content|timestamp", "titles": self._title}
            result = self._site._api_query(params)

        res = result["query"]["pages"].values()[0]
        try:
            self._content = res["revisions"][0]["*"]
            self._basetimestamp = res["revisions"][0]["timestamp"]
        except KeyError:
            # This can only happen if the page was deleted since we last called
            # self._load_attributes(). In that case, some of our attributes are
            # outdated, so force another self._load_attributes():
            self._load_attributes()
            self._force_existence()

    def _edit(self, params=None, text=None, summary=None, minor=None, bot=None,
              force=None, section=None, captcha_id=None, captcha_word=None,
              tries=0):
        """Edit the page!

        If `params` is given, we'll use it as our API query parameters.
        Otherwise, we'll build params using the given kwargs via
        _build_edit_params().
        
        We'll then try to do the API query, and catch any errors the API raises
        in _handle_edit_errors(). We'll then throw these back as subclasses of
        EditError.
        """
        # Try to get our edit token, and die if we can't:
        if not self._token:
            self._load_attributes()
        if not self._token:
            e = "You don't have permission to edit this page."
            raise PermissionsError(e)
        
        # Weed out invalid pages before we get too far:
        self._force_validity()

        # Build our API query string:
        if not params:
            params = self._build_edit_params(text, summary, minor, bot, force,
                                             section, captcha_id, captcha_word)
        else: # Make sure we have the right token:
            params["token"] = self._token

        # Try the API query, catching most errors with our handler:
        try:
            result = self._site._api_query(params)
        except SiteAPIError as error:
            if not hasattr(error, "code"):
                raise  # We can only handle errors with a code attribute
            result = self._handle_edit_errors(error, params, tries)

        # If everything was successful, reset invalidated attributes:
        if result["edit"]["result"] == "Success":
            self._content = None
            self._basetimestamp = None
            self._exists = 0
            return

        # If we're here, then the edit failed. If it's because of AssertEdit,
        # handle that. Otherwise, die - something odd is going on:
        try:
            assertion = result["edit"]["assert"]
        except KeyError:
            raise EditError(result["edit"])
        self._handle_assert_edit(assertion, params, tries)

    def _build_edit_params(self, text, summary, minor, bot, force, section,
                           captcha_id, captcha_word):
        """Given some keyword arguments, build an API edit query string."""
        hashed = md5(text).hexdigest()  # Checksum to ensure text is correct
        params = {"action": "edit", "title": self._title, "text": text,
                  "token": self._token, "summary": summary, "md5": hashed}

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
            params["starttimestamp"] = self._starttimestamp
            if self._basetimestamp:
                params["basetimestamp"] = self._basetimestamp
            if self._exists == 2:
                # Page does not exist; don't edit if it already exists:
                params["createonly"] = "true"
        else:
            params["recreate"] = "true"            

        return params

    def _handle_edit_errors(self, error, params, tries):
        """If our edit fails due to some error, try to handle it.

        We'll either raise an appropriate exception (for example, if the page
        is protected), or we'll try to fix it (for example, if we can't edit
        due to being logged out, we'll try to log in).
        """
        if error.code in ["noedit", "cantcreate", "protectedtitle",
                          "noimageredirect"]:
            raise PermissionsError(error.info)

        elif error.code in ["noedit-anon", "cantcreate-anon",
                            "noimageredirect-anon"]:
            if not all(self._site._login_info):
                # Insufficient login info:
                raise PermissionsError(error.info)
            if tries == 0:
                # We have login info; try to login:
                self._site._login(self._site._login_info)
                self._token = None  # Need a new token; old one is invalid now
                return self._edit(params=params, tries=1)
            else:
                # We already tried to log in and failed!
                e = "Although we should be logged in, we are not. This may be a cookie problem or an odd bug."
                raise LoginError(e)

        elif error.code in ["editconflict", "pagedeleted", "articleexists"]:
            # These attributes are now invalidated:
            self._content = None
            self._basetimestamp = None
            self._exists = 0
            raise EditConflictError(error.info)

        elif error.code in ["emptypage", "emptynewsection"]:
            raise NoContentError(error.info)

        elif error.code == "contenttoobig":
            raise ContentTooBigError(error.info)

        elif error.code == "spamdetected":
            raise SpamDetectedError(error.info)

        elif error.code == "filtered":
            raise FilteredError(error.info)

        raise EditError(": ".join((error.code, error.info)))

    def _handle_assert_edit(self, assertion, params, tries):
        """If we can't edit due to a failed AssertEdit assertion, handle that.

        If the assertion was 'user' and we have valid login information, try to
        log in. Otherwise, raise PermissionsError with details.
        """
        if assertion == "user":
            if not all(self._site._login_info):
                # Insufficient login info:
                e = "AssertEdit: user assertion failed, and no login info was provided."
                raise PermissionsError(e)
            if tries == 0:
                # We have login info; try to login:
                self._site._login(self._site._login_info)
                self._token = None  # Need a new token; old one is invalid now
                return self._edit(params=params, tries=1)
            else:
                # We already tried to log in and failed!
                e = "Although we should be logged in, we are not. This may be a cookie problem or an odd bug."
                raise LoginError(e)

        elif assertion == "bot":
            e = "AssertEdit: bot assertion failed; we don't have a bot flag!"
            raise PermissionsError(e)

        # Unknown assertion, maybe "true", "false", or "exists":
        e = "AssertEdit: assertion '{0}' failed.".format(assertion)
        raise PermissionsError(e)

    def title(self, force=False):
        """Returns the Page's title, or pagename.

        This won't do any API queries on its own unless force is True, in which
        case the title will be forcibly reloaded from the API (normalizing it,
        and following redirects if follow_redirects=True was passed to
        __init__()). Any other methods that do API queries will reload title on
        their own, however, like exists() and get().
        """
        if force:
            self._load_wrapper()
        return self._title

    def exists(self, force=False):
        """Returns information about whether the Page exists or not.

        The returned "information" is a tuple with two items. The first is a
        bool, either True if the page exists or False if it does not. The
        second is a string giving more information, either "invalid", (title
        is invalid, e.g. it contains "["), "missing", or "exists".

        Makes an API query if force is True or if we haven't already made one.
        """
        cases = {
            0: (None, "unknown"),
            1: (False, "invalid"),
            2: (False, "missing"),
            3: (True, "exists"),
        }
        if self._exists == 0 or force:
            self._load_wrapper()
        return cases[self._exists]

    def pageid(self, force=False):
        """Returns an integer ID representing the Page.

        Makes an API query if force is True or if we haven't already made one.

        Raises InvalidPageError or PageNotFoundError if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._exists == 0 or force:
            self._load_wrapper()
        self._force_existence()  # missing pages do not have IDs
        return self._pageid

    def url(self, force=False):
        """Returns the page's URL.

        Like title(), this won't do any API queries on its own unless force is
        True. If the API was never queried for this page, we will attempt to
        determine the URL ourselves based on the title.
        """
        if force:
            self._load_wrapper()
        if self._fullurl is not None:
            return self._fullurl
        else:
            slug = quote(self._title.replace(" ", "_"), safe="/:")
            path = self._site._article_path.replace("$1", slug)
            return ''.join((self._site._base_url, path))

    def namespace(self, force=False):
        """Returns the page's namespace ID (an integer).

        Like title(), this won't do any API queries on its own unless force is
        True. If the API was never queried for this page, we will attempt to
        determine the namespace ourselves based on the title.
        """
        if force:
            self._load_wrapper()
        return self._namespace

    def protection(self, force=False):
        """Returns the page's current protection status.

        Makes an API query if force is True or if we haven't already made one.

        Raises InvalidPageError if the page name is invalid. Will not raise an
        error if the page is missing because those can still be protected.
        """
        if self._exists == 0 or force:
            self._load_wrapper()
        self._force_validity()  # invalid pages cannot be protected
        return self._protection

    def creator(self, force=False):
        """Returns the page's creator (i.e., the first user to edit the page).

        Makes an API query if force is True or if we haven't already made one.
        Normally, we can get the creator along with everything else (except
        content) in self._load_attributes(). However, due to a limitation in
        the API (can't get the editor of one revision and the content of
        another at both ends of the history), if our other attributes were only
        loaded from get(), we'll have to do another API query. This is done
        by calling ourselves again with force=True.

        Raises InvalidPageError or PageNotFoundError if the page name is
        invalid or the page does not exist, respectively.
        """
        if self._exists == 0 or force:
            self._load_wrapper()
        self._force_existence()
        if not self._creator and not force:
            self.creator(force=True)
        return self._creator

    def is_talkpage(self, force=False):
        """Returns True if the page is a talkpage, else False.

        Like title(), this won't do any API queries on its own unless force is
        True. If the API was never queried for this page, we will attempt to
        determine the talkpage status ourselves based on its namespace ID.
        """
        if force:
            self._load_wrapper()
        return self._is_talkpage

    def is_redirect(self, force=False):
        """Returns True if the page is a redirect, else False.

        Makes an API query if force is True or if we haven't already made one.

        We will return False even if the page does not exist or is invalid.
        """
        if self._exists == 0 or force:
            self._load_wrapper()
        return self._is_redirect

    def toggle_talk(self, force=False, follow_redirects=None):
        """Returns a content page's talk page, or vice versa.

        The title of the new page is determined by namespace logic, not API
        queries. We won't make any API queries on our own unless force is True,
        and the only reason then would be to forcibly update the title or
        follow redirects if we haven't already made an API query.

        If `follow_redirects` is anything other than None (the default), it
        will be passed to the new Page's __init__(). Otherwise, we'll use the
        value passed to our own __init__().

        Will raise InvalidPageError if we try to get the talk page of a special
        page (in the Special: or Media: namespaces), but we won't raise an
        exception if our page is otherwise missing or invalid.
        """
        if force:
            self._load_wrapper()
        if self._namespace < 0:
            ns = self._site.namespace_id_to_name(self._namespace)
            e = "Pages in the {0} namespace can't have talk pages.".format(ns)
            raise InvalidPageError(e)

        if self._is_talkpage:
            new_ns = self._namespace - 1
        else:
            new_ns = self._namespace + 1

        try:
            body = self._title.split(":", 1)[1]
        except IndexError:
            body = self._title

        new_prefix = self._site.namespace_id_to_name(new_ns)

        # If the new page is in namespace 0, don't do ":Title" (it's correct,
        # but unnecessary), just do "Title":
        if new_prefix:
            new_title = ':'.join((new_prefix, body))
        else:
            new_title = body

        if follow_redirects is None:
            follow_redirects = self._follow_redirects
        return Page(self._site, new_title, follow_redirects)

    def get(self, force=False):
        """Returns page content, which is cached if you try to call get again.

        Use `force` to forcibly reload page content even if we've already
        loaded some. This is good if you want to edit a page multiple times,
        and you want to get updated content before you make your second edit.

        Raises InvalidPageError or PageNotFoundError if the page name is
        invalid or the page does not exist, respectively.
        """
        if force or self._exists == 0:
            # Kill two birds with one stone by doing an API query for both our
            # attributes and our page content:
            params = {"action": "query", "rvlimit": 1, "titles": self._title,
                      "prop": "info|revisions", "inprop": "protection|url",
                      "intoken": "edit", "rvprop": "content|timestamp"}
            result = self._site._api_query(params)
            self._load_attributes(result=result)
            self._force_existence()
            self._load_content(result=result)

            # Follow redirects if we're told to:
            if self._keep_following and self._is_redirect:
                self._title = self.get_redirect_target()
                self._keep_following = False  # don't follow double redirects
                self._content = None  # reset the content we just loaded
                self.get(force=True)

            return self._content

        # Make sure we're dealing with a real page here. This may be outdated
        # if the page was deleted since we last called self._load_attributes(),
        # but self._load_content() can handle that:
        self._force_existence()

        if self._content is None:
            self._load_content()

        return self._content

    def get_redirect_target(self, force=False):
        """If the page is a redirect, returns its destination.

        Use `force` to forcibly reload content even if we've already loaded
        some before. Note that this method calls get() for page content.

        Raises InvalidPageError or PageNotFoundError if the page name is
        invalid or the page does not exist, respectively. Raises RedirectError
        if the page is not a redirect.
        """
        content = self.get(force)
        try:
            return re.findall(self.re_redirect, content, flags=re.I)[0]
        except IndexError:
            e = "The page does not appear to have a redirect target."
            raise RedirectError(e)

    def edit(self, text, summary, minor=False, bot=True, force=False):
        """Replaces the page's content or creates a new page.

        `text` is the new page content, with `summary` as the edit summary.
        If `minor` is True, the edit will be marked as minor. If `bot` is true,
        the edit will be marked as a bot edit, but only if we actually have a
        bot flag.

        Use `force` to push the new content even if there's an edit conflict or
        the page was deleted/recreated between getting our edit token and
        editing our page. Be careful with this!
        """
        self._edit(text=text, summary=summary, minor=minor, bot=bot,
                   force=force)

    def add_section(self, text, title, minor=False, bot=True, force=False):
        """Adds a new section to the bottom of the page.

        The arguments for this are the same as those for edit(), but instead of
        providing a summary, you provide a section title.

        Likewise, raised exceptions are the same as edit()'s.

        This should create the page if it does not already exist, with just the
        new section as content.
        """
        self._edit(text=text, summary=title, minor=minor, bot=bot, force=force,
                   section="new")
