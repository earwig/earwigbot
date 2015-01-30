# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

    *Attributes:*

    - :py:attr:`size`:    the total number of members in the category
    - :py:attr:`pages`:   the number of pages in the category
    - :py:attr:`files`:   the number of files in the category
    - :py:attr:`subcats`: the number of subcategories in the category

    *Public methods:*

    - :py:meth:`get_members`: iterates over Pages in the category
    """

    def __repr__(self):
        """Return the canonical string representation of the Category."""
        res = "Category(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Return a nice string representation of the Category."""
        return '<Category "{0}" of {1}>'.format(self.title, str(self.site))

    def __iter__(self):
        """Iterate over all members of the category."""
        return self.get_members()

    def _get_members_via_api(self, limit, follow):
        """Iterate over Pages in the category using the API."""
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": self.title, "continue": ""}

        while 1:
            params["cmlimit"] = limit if limit else "max"
            result = self.site.api_query(**params)
            for member in result["query"]["categorymembers"]:
                title = member["title"]
                yield self.site.get_page(title, follow_redirects=follow)

            if "continue" in result:
                params.update(result["continue"])
                if limit:
                    limit -= len(result["query"]["categorymembers"])
            else:
                break

    def _get_members_via_sql(self, limit, follow):
        """Iterate over Pages in the category using SQL."""
        query = """SELECT page_title, page_namespace, page_id FROM page
                   JOIN categorylinks ON page_id = cl_from
                   WHERE cl_to = ?"""
        title = self.title.replace(" ", "_").split(":", 1)[1]

        if limit:
            query += " LIMIT ?"
            result = self.site.sql_query(query, (title, limit), buffsize=0)
        else:
            result = self.site.sql_query(query, (title,), buffsize=0)

        members = list(result)
        for row in members:
            base = row[0].replace("_", " ").decode("utf8")
            namespace = self.site.namespace_id_to_name(row[1])
            if namespace:
                title = u":".join((namespace, base))
            else:  # Avoid doing a silly (albeit valid) ":Pagename" thing
                title = base
            yield self.site.get_page(title, follow_redirects=follow,
                                     pageid=row[2])

    def _get_size_via_api(self, member_type):
        """Return the size of the category using the API."""
        result = self.site.api_query(action="query", prop="categoryinfo",
                                     titles=self.title)
        info = result["query"]["pages"].values()[0]["categoryinfo"]
        return info[member_type]

    def _get_size_via_sql(self, member_type):
        """Return the size of the category using SQL."""
        query = "SELECT COUNT(*) FROM categorylinks WHERE cl_to = ?"
        title = self.title.replace(" ", "_").split(":", 1)[1]
        if member_type == "size":
            result = self.site.sql_query(query, (title,))
        else:
            query += " AND cl_type = ?"
            result = self.site.sql_query(query, (title, member_type[:-1]))
        return list(result)[0][0]

    def _get_size(self, member_type):
        """Return the size of the category."""
        services = {
            self.site.SERVICE_API: self._get_size_via_api,
            self.site.SERVICE_SQL: self._get_size_via_sql
        }
        return self.site.delegate(services, (member_type,))

    @property
    def size(self):
        """The total number of members in the category.

        Includes pages, files, and subcats. Equal to :py:attr:`pages` +
        :py:attr:`files` + :py:attr:`subcats`. This will use either the API or
        SQL depending on which are enabled and the amount of lag on each. This
        is handled by :py:meth:`site.delegate()
        <earwigbot.wiki.site.Site.delegate>`.
        """
        return self._get_size("size")

    @property
    def pages(self):
        """The number of pages in the category.

        This will use either the API or SQL depending on which are enabled and
        the amount of lag on each. This is handled by :py:meth:`site.delegate()
        <earwigbot.wiki.site.Site.delegate>`.
        """
        return self._get_size("pages")

    @property
    def files(self):
        """The number of files in the category.

        This will use either the API or SQL depending on which are enabled and
        the amount of lag on each. This is handled by :py:meth:`site.delegate()
        <earwigbot.wiki.site.Site.delegate>`.
        """
        return self._get_size("files")

    @property
    def subcats(self):
        """The number of subcategories in the category.

        This will use either the API or SQL depending on which are enabled and
        the amount of lag on each. This is handled by :py:meth:`site.delegate()
        <earwigbot.wiki.site.Site.delegate>`.
        """
        return self._get_size("subcats")

    def get_members(self, limit=None, follow_redirects=None):
        """Iterate over Pages in the category.

        If *limit* is given, we will provide this many pages, or less if the
        category is smaller. By default, *limit* is ``None``, meaning we will
        keep iterating over members until the category is exhausted.
        *follow_redirects* is passed directly to :py:meth:`site.get_page()
        <earwigbot.wiki.site.Site.get_page>`; it defaults to ``None``, which
        will use the value passed to our :py:meth:`__init__`.

        This will use either the API or SQL depending on which are enabled and
        the amount of lag on each. This is handled by :py:meth:`site.delegate()
        <earwigbot.wiki.site.Site.delegate>`.

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
        services = {
            self.site.SERVICE_API: self._get_members_via_api,
            self.site.SERVICE_SQL: self._get_members_via_sql
        }
        if follow_redirects is None:
            follow_redirects = self._follow_redirects
        return self.site.delegate(services, (limit, follow_redirects))
