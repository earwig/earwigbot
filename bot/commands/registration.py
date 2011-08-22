# -*- coding: utf-8  -*-

import time

from classes import BaseCommand
import wiki

class Command(BaseCommand):
    """Return when a user registered."""
    name = "registration"

    def check(self, data):
        commands = ["registration", "age"]
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
            reg = user.registration()
        except wiki.UserNotFoundError:
            msg = "the user \x0302{0}\x0301 does not exist."
            self.connection.reply(data, msg.format(name))
            return

        date = time.strftime("%b %m, %Y at %H:%M:%S %Z", reg)
        age = self.get_diff(time.mktime(reg), time.mktime(time.gmtime()))

        g = user.gender()
        if g == "male":
            gender = "He's"
        elif g == "female":
            gender = "She's"
        else:
            gender = "They're"
        
        msg = "\x0302{0}\x0301 registered on {1}. {2} {3} old."
        self.connection.reply(data, msg.format(name, date, gender, age))

    def get_diff(self, t1, t2):
        parts = {"years": 31536000, "days": 86400, "hours": 3600,
                 "minutes": 60, "seconds": 1}
        msg = []

        order = sorted(parts.items(), key=lambda x: x[1], reverse=True)
        for key, value in order:
            num = 0
            while t2 - t1 > value:
                t1 += value
                num += 1
            if num or (not num and msg):
                msg.append(" ".join((str(num), key)))

        return ", ".join(msg)
