# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

import time

from earwigbot import exceptions
from earwigbot.commands import Command

class Registration(Command):
    """Return when a user registered."""
    name = "registration"
    commands = ["registration", "reg", "age"]

    def process(self, data):
        if not data.args:
            name = data.nick
        else:
            name = ' '.join(data.args)

        site = self.bot.wiki.get_site()
        user = site.get_user(name)

        try:
            reg = user.registration
        except exceptions.UserNotFoundError:
            msg = "The user \x0302{0}\x0F does not exist."
            self.reply(data, msg.format(name))
            return

        date = time.strftime("%b %d, %Y at %H:%M:%S UTC", reg)
        age = self.get_diff(time.mktime(reg), time.mktime(time.gmtime()))

        if user.gender == "male":
            gender = "He's"
        elif user.gender == "female":
            gender = "She's"
        else:
            gender = "They're"  # Singular they?

        msg = "\x0302{0}\x0F registered on {1}. {2} {3} old."
        self.reply(data, msg.format(name, date, gender, age))

    def get_diff(self, t1, t2):
        parts = [("year", 31536000), ("day", 86400), ("hour", 3600),
                 ("minute", 60), ("second", 1)]
        msg = []
        for name, size in parts:
            num = int(t2 - t1) / size
            t1 += num * size
            if num:
                chunk = "{0} {1}".format(num, name if num == 1 else name + "s")
                msg.append(chunk)
        return ", ".join(msg) if msg else "0 seconds"
