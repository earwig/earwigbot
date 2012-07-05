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

from earwigbot.wiki.page import Page

__all__ = ["Category"]

class Category(Page):
    """
    **EarwigBot: Wiki Toolset: Category**

    Represents a category on a given :py:class:`~earwigbot.wiki.site.Site`, a
    subclass of :py:class:`~earwigbot.wiki.page.Page`. Provides additional
    methods, but :py:class:`~earwigbot.wiki.page.Page`'s own methods should
    work fine on :py:class:`Category` objects. :py:meth:`site.get_page()
    <earwigbot.wiki.site.Site.get_page>` will return a :py:class:`Category`
    instead of a :py:class:`~earwigbot.wiki.page.Page` if the given title is in
    the category namespace; :py:meth:`~earwigbot.wiki.site.Site.get_category`
    is shorthand, accepting category names without the namespace prefix.

    *Public methods:*

    - :py:meth:`get_members`: iterates over Pages in the category
    """

    def __repr__(self):
        """Return the canonical string representation of the Category."""
        res = "Category(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Return a nice string representation of the Category."""
        return '<Category "{0}" of {1}>'.format(self.title, str(self._site))

    def _get_members_via_sql(self, limit, follow):
        """Iterate over Pages in the category using SQL."""
        query = """SELECT page_title, page_namespace, page_id FROM page
                   JOIN categorylinks ON page_id = cl_from
                   WHERE cl_to = ?"""
        title = self.title.replace(" ", "_").split(":", 1)[1]

        if limit:
            query += " LIMIT ?"
            result = self._site.sql_query(query, (title, limit))
        else:
            result = self._site.sql_query(query, (title,))

        members = list(result)
        for row in members:
            base = row[0].replace("_", " ").decode("utf8")
            namespace = self._site.namespace_id_to_name(row[1])
            if namespace:
                title = u":".join((namespace, base))
            else:  # Avoid doing a silly (albeit valid) ":Pagename" thing
                title = base
            yield self._site.get_page(title, follow_redirects=follow,
                                      pageid=row[2])

    def _get_members_via_api(self, limit, follow):
        """Iterate over Pages in the category using the API."""
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": self._title}

        while 1:
            params["cmlimit"] = limit if limit else "max"
            result = self._site.api_query(**params)
            for member in result["query"]["categorymembers"]:
                title = member["title"]
                yield self._site.get_page(title, follow_redirects=follow)

            if "query-continue" in result:
                qcontinue = result["query-continue"]["categorymembers"]
                params["cmcontinue"] = qcontinue["cmcontinue"]
                if limit:
                    limit -= len(result["query"]["categorymembers"])
            else:
                break

    def get_members(self, use_sql=False, limit=None, follow_redirects=None):
        """Iterate over Pages in the category.

        If *use_sql* is ``True``, we will use a SQL query instead of the API.
        Note that pages are retrieved from the API in chunks (by default, in
        500-page chunks for normal users and 5000-page chunks for bots and
        admins), so queries may be made as we go along. If *limit* is given, we
        will provide this many pages, or less if the category is smaller. By
        default, *limit* is ``None``, meaning we will keep iterating over
        members until the category is exhausted. *follow_redirects* is passed
        directly to :py:meth:`site.get_page()
        <earwigbot.wiki.site.Site.get_page>`; it defaults to ``None``, which
        will use the value passed to our :py:meth:`__init__`.

        .. note::
           Be careful when iterating over very large categories with no limit.
           If using the API, at best, you will make one query per 5000 pages,
           which can add up significantly for categories with hundreds of
           thousands of members. As for SQL, note that *all page titles are
           stored internally* as soon as the query is made, so the site-wide
           SQL lock can be freed and unrelated queries can be made without
           requiring a separate connection to be opened. This is generally not
           an issue unless your category's size approaches several hundred
           thousand, in which case the sheer number of titles in memory becomes
           problematic.
        """
        if follow_redirects is None:
            follow_redirects = self._follow_redirects
        if use_sql:
            return self._get_members_via_sql(limit, follow_redirects)
        else:
            return self._get_members_via_api(limit, follow_redirects)
