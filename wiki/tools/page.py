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

    def get(self):
        """
        Docstring needed
        """
        params = {'action': 'query', 'prop': 'revisions', 'rvprop':'content', 'rvlimit':'1'}
        params["titles"] = self.title
        result = self.site.api_query(params)
        pageid = result['query']['pages'].keys()[0]
        content = result['query']['pages'][pageid]['revisions'][0]['*']
        return content
