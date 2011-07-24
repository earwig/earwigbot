# -*- coding: utf-8  -*-

class User(object):
    """
    EarwigBot's Wiki Toolset: User Class
    """

    def __init__(self, site, username):
        """
        Docstring needed
        """
        self.site = site
        self.username = username

    def exists(self):
        """
        Docstring needed
        """
        pass

    def get_rights(self):
        """
        Docstring needed
        """
        params = {"action": "query", "list": "users", "usprop": "groups",
            "ususers": self.username}
        result = self.site.api_query(params)
        try:
            rights = res['query']['users'][0]['groups']
        except KeyError:  # 'groups' not found, meaning the user does not exist
            return None
        return rights
