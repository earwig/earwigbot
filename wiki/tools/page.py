# -*- coding: utf-8  -*-

class Page(object):
    """
    EarwigBot's Wiki Toolset: Page Class
    """

    def __init__(self, site, title):
        """
        Docstring needed
        """
        self.site = site
        self.title = title
        self._content = None

    def exists(self):
        """
        Docstring needed
        """
        pass

    def get(self, force_reload=False):
        """
        Docstring needed
        """
        if content is None or force_reload:
            params = {"action": "query", "prop": "revisions",
                "rvprop": "content", "rvlimit": 1, "titles": self.title}
            result = self.site.api_query(params)
            content = result["query"]["pages"].values()[0]["revisions"][0]["*"]
            self._content = content
            return content
        return self._content
