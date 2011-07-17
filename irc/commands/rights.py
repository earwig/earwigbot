# -*- coding: utf-8  -*-

"""
Retrieve a list of user rights for a given username via the API.
"""

import json
import urllib

from irc.classes import BaseCommand

class Rights(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Retrieve a list of rights for a given username."

    def check(self, data):
        if data.is_command and data.command in ["rights", "groups", "permissions", "privileges"]:
            return True
        return False

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "what user do you want me to look up?")
            return

        username = ''.join(data.args)
        rights = self.get_rights(username)
        if rights:
            self.connection.reply(data, "the rights for user \x0302{0}\x0301 are {1}.".format(username, ', '.join(rights)))
        else:
            self.connection.reply(data, "the user x0302{0}\x0301 has no rights, or does not exist.".format(username))

    def get_rights(self, username):
        params = {'action': 'query', 'format': 'json', 'list': 'users', 'usprop': 'groups'}
        params['ususers'] = username
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        try:
            rights = res['query']['users'][0]['groups']
        except KeyError:  # 'groups' not found, meaning the user does not exist
            return None
        try:
            rights.remove("*")  # remove the implicit '*' group given to everyone
        except ValueError:  # I don't expect this to happen, but if it does, be prepared
            pass
        return rights
