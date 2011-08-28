# -*- coding: utf-8  -*-

from classes import BaseCommand
import wiki

class Command(BaseCommand):
    """Retrieve a list of rights for a given username."""
    name = "rights"

    def check(self, data):
        commands = ["rights", "groups", "permissions", "privileges"]
        if data.is_command and data.command in commands:
            return True
        return False

    def process(self, data):
        if not data.args:
            name = data.nick
        else:
            name = ' '.join(data.args)

        site = wiki.get_site()
        site._maxlag = None
        user = site.get_user(name)

        try:
            rights = user.groups()
        except wiki.UserNotFoundError:
            msg = "the user \x0302{0}\x0301 does not exist."
            self.connection.reply(data, msg.format(name))
            return

        try:
            rights.remove("*")  # Remove the '*' group given to everyone
        except ValueError:
            pass
        msg = "the rights for \x0302{0}\x0301 are {1}."
        self.connection.reply(data, msg.format(name, ', '.join(rights)))
