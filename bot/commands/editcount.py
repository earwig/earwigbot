# -*- coding: utf-8  -*-

from urllib import quote_plus

from classes import BaseCommand
import wiki

class Command(BaseCommand):
    """Return a user's edit count."""
    name = "editcount"

    def check(self, data):
        commands = ["ec", "editcount"]
        if data.is_command and data.command in commands:
            return True
        return False

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "who do you want me to look up?")
            return

        username = ' '.join(data.args)
        site = wiki.get_site()
        site._maxlag = None
        user = site.get_user(username)

        try:
            count = user.editcount()
        except wiki.UserNotFoundError:
            msg = "the user \x0302{0}\x0301 does not exist."
            self.connection.reply(data, msg.format(username))
            return

        url = "http://toolserver.org/~soxred93/pcount/index.php?name={0}&lang=en&wiki=wikipedia"
        url = url.format(quote_plus(user.name()))

        msg = "\x0302{0}\x0301 has {1} edits ({2})."
        self.connection.reply(data, msg.format(username, count, url))
