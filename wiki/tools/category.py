# -*- coding: utf-8  -*-

from wiki.tools.page import Page

class Category(Page):
    """
    EarwigBot's Wiki Toolset: Category Class

    Represents a Category on a given Site, a subclass of Page. Provides
    additional methods, but Page's own methods should work fine on Category
    objects. Site.get_page() will return a Category instead of a Page if the
    given title is in the category namespace; get_category() is shorthand,
    because it accepts category names without the namespace prefix.

    Public methods:
    members -- returns a list of titles in the category
    """

    def members(self, limit=50):
        """Returns a list of titles in the category.

        If `limit` is provided, we will provide this many titles, or less if
        the category is too small. `limit` defaults to 50; normal users can go
        up to 500, and bots can go up to 5,000 on a single API query.
        """
        params = {"action": "query", "list": "categorymembers",
            "cmlimit": limit, "cmtitle": self.title}
        result = self._site._api_query(params)
        members = result['query']['categorymembers']
        return [member["title"] for member in members]
