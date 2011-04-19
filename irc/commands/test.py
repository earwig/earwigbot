# -*- coding: utf-8  -*-

# A very simple command to test the bot.

import random

from irc.base_command import BaseCommand

class Test(BaseCommand):
    def get_hook(self):
        return "msg"

    def get_help(self, command):
        return "Test the bot!"

    def check(self, data):
        if data.is_command and data.command == "test":
            return True
        return False

    def process(self, data):
        hey = random.randint(0, 1)
        if hey:
            self.connection.say(data.chan, "Hey \x02%s\x0F!" % data.nick)
        else:
            self.connection.say(data.chan, "'sup \x02%s\x0F?" % data.nick)
