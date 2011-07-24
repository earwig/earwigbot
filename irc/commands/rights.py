# -*- coding: utf-8  -*-

"""
Retrieve a list of user rights for a given username via the API.
"""

from irc.classes import BaseCommand
from wiki import tools

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

        username = ' '.join(data.args)
        site = tools.get_site()
        user = site.get_user(username)
        rights = user.get_rights()
        if rights:
            try:
                rights.remove("*")  # remove the implicit '*' group given to everyone
            except ValueError:
                pass
            self.connection.reply(data, "the rights for \x0302{0}\x0301 are {1}.".format(username, ', '.join(rights)))
        else:
            self.connection.reply(data, "the user \x0302{0}\x0301 has no rights, or does not exist.".format(username))
