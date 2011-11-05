# -*- coding: utf-8  -*-

from wiki.page import Page

class Category(Page):
    """
    EarwigBot's Wiki Toolset: Category Class

    Represents a Category on a given Site, a subclass of Page. Provides
    additional methods, but Page's own methods should work fine on Category
    objects. Site.get_page() will return a Category instead of a Page if the
    given title is in the category namespace; get_category() is shorthand,
    because it accepts category names without the namespace prefix.

    Public methods:
    members -- returns a list of pages in the category as (title, id) tuples
    """

    def __repr__(self):
        """Returns the canonical string representation of the Category."""
        res = "Category(title={0!r}, follow_redirects={1!r}, site={2!r})"
        return res.format(self._title, self._follow_redirects, self._site)

    def __str__(self):
        """Returns a nice string representation of the Category."""
        return '<Category "{0}" of {1}>'.format(self.title(), str(self._site))

    def members(self, limit=50):
        """Returns a list of pages in the category as (title, pageid) tuples.

        If `limit` is provided, we will provide this many titles, or less if
        the category is too small. `limit` defaults to 50; normal users can go
        up to 500, and bots can go up to 5,000 on a single API query.
        """
        params = {"action": "query", "list": "categorymembers",
            "cmlimit": limit, "cmtitle": self._title}
        result = self._site._api_query(params)
        members = result['query']['categorymembers']
        return [(member["title"], member["pageid"]) for member in members]
