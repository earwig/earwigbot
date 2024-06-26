# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from urllib.parse import quote_plus

from earwigbot import exceptions
from earwigbot.commands import Command


class Editcount(Command):
    """Return a user's edit count."""

    name = "editcount"
    commands = ["ec", "editcount"]

    def process(self, data):
        if not data.args:
            name = data.nick
        else:
            name = " ".join(data.args)

        site = self.bot.wiki.get_site()
        user = site.get_user(name)

        try:
            count = user.editcount
        except exceptions.UserNotFoundError:
            msg = "The user \x0302{0}\x0f does not exist."
            self.reply(data, msg.format(name))
            return

        safe = quote_plus(user.name.encode("utf8"))
        url = f"https://xtools.wmflabs.org/ec/{site.domain}/{safe}"
        fullurl = url.format(safe, site.domain)
        msg = "\x0302{0}\x0f has {1} edits ({2})."
        self.reply(data, msg.format(name, count, fullurl))
