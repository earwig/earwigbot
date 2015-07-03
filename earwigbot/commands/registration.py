# -*- coding: utf-8  -*-
#
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

from datetime import datetime
from time import mktime

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

        dt = datetime.fromtimestamp(mktime(reg))
        date = dt.strftime("%b %d, %Y at %H:%M:%S UTC")
        age = self.get_age(dt)

        if user.gender == "male":
            gender = "He's"
        elif user.gender == "female":
            gender = "She's"
        else:
            gender = "They're"  # Singular they?

        msg = "\x0302{0}\x0F registered on {1}. {2} {3} old."
        self.reply(data, msg.format(name, date, gender, age))

    def get_age(self, birth):
        msg = []
        def insert(unit, num):
            if not num:
                return
            msg.append("{0} {1}".format(num, unit if num == 1 else unit + "s"))

        now = datetime.utcnow()
        bd_passed = now.timetuple()[1:-3] < birth.timetuple()[1:-3]
        years = now.year - birth.year - bd_passed
        delta = now - birth.replace(year=birth.year + years)
        insert("year", years)
        insert("day", delta.days)

        seconds = delta.seconds
        units = [("hour", 3600), ("minute", 60), ("second", 1)]
        for unit, size in units:
            num = seconds / size
            seconds -= num * size
            insert(unit, num)
        return ", ".join(msg) if msg else "0 seconds"
