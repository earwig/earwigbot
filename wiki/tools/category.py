# -*- coding: utf-8  -*-

from wiki.tools.page import Page

class Category(Page):
    """
    EarwigBot's Wiki Toolset: Category Class
    """

    def get_members(limit=50):
        """
        Docstring needed
        """
        params = {"action": "query", "list": "categorymembers", "cmlimit": limit}
        params["cmtitle"] = self.title
        result = self.site.api_query(params)
        members = result['query']['categorymembers']
        return [member["title"] for member in members]
