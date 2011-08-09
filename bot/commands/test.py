# -*- coding: utf-8  -*-

import random

from classes import BaseCommand

class Command(BaseCommand):
    """Test the bot!"""
    name = "test"

    def process(self, data):
        hey = random.randint(0, 1)
        if hey:
            self.connection.say(data.chan, "Hey \x02%s\x0F!" % data.nick)
        else:
            self.connection.say(data.chan, "'sup \x02%s\x0F?" % data.nick)
