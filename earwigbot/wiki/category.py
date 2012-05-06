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
    **EarwigBot's Wiki Toolset: Category Class**

    Represents a category on a given :py:class:`~earwigbot.wiki.site.Site`, a
    subclass of :py:class:`~earwigbot.wiki.page.Page`. Provides additional
    methods, but :py:class:`~earwigbot.wiki.page.Page`'s own methods should
    work fine on :py:class:`Category` objects. :py:meth:`site.get_page()
    <earwigbot.wiki.site.Site.get_page>` will return a :py:class:`Category`
    instead of a :py:class:`~earwigbot.wiki.page.Page` if the given title is in
    the category namespace; :py:meth:`~earwigbot.wiki.site.Site.get_category`
    is shorthand, accepting category names without the namespace prefix.

    *Public methods:*

    - :py:meth:`get_members`: returns a list of page titles in the category
    """

    def __repr__(self):
        """Returns the canonical string representation of the Category."""
        res = "Category(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Returns a nice string representation of the Category."""
        return '<Category "{0}" of {1}>'.format(self.title(), str(self._site))

    def _get_members_via_sql(self, limit):
        """Return a list of tuples of (title, pageid) in the category."""
        query = """SELECT page_title, page_namespace, page_id FROM page
                   JOIN categorylinks ON page_id = cl_from
                   WHERE cl_to = ?"""
        title = self.title().replace(" ", "_").split(":", 1)[1]

        if limit:
            query += " LIMIT ?"
            result = self._site.sql_query(query, (title, limit))
        else:
            result = self._site.sql_query(query, (title,))

        members = []
        for row in result:
            base = row[0].replace("_", " ").decode("utf8")
            namespace = self._site.namespace_id_to_name(row[1])
            if namespace:
                title = u":".join((namespace, base))
            else:  # Avoid doing a silly (albeit valid) ":Pagename" thing
                title = base
            members.append((title, row[2]))
        return members

    def _get_members_via_api(self, limit):
        """Return a list of page titles in the category using the API."""
        params = {"action": "query", "list": "categorymembers",
                  "cmlimit": limit, "cmtitle": self._title}
        if not limit:
            params["cmlimit"] = 50  # Default value

        result = self._site.api_query(**params)
        members = result['query']['categorymembers']
        return [member["title"] for member in members]

    def get_members(self, use_sql=False, limit=None):
        """Returns a list of page titles in the category.

        If *use_sql* is ``True``, we will use a SQL query instead of the API.
        Pages will be returned as tuples of ``(title, pageid)`` instead of just
        titles.

        If *limit* is provided, we will provide this many titles, or less if
        the category is smaller. It defaults to 50 for API queries; normal
        users can go up to 500, and bots can go up to 5,000 on a single API
        query. If we're using SQL, the limit is ``None`` by default (returning
        all pages in the category), but an arbitrary limit can still be chosen.
        """
        if use_sql:
            return self._get_members_via_sql(limit)
        else:
            return self._get_members_via_api(limit)
