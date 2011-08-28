# -*- coding: utf-8  -*-

import random

from classes import BaseCommand

class Command(BaseCommand):
    """Praise people!"""
    name = "praise"

    def check(self, data):
        commands = ["praise", "earwig", "leonard", "leonard^bloom", "groove",
                  "groovedog"]
        return data.is_command and data.command in commands

    def process(self, data):
        if data.command == "earwig":
            msg = "\x02Earwig\x0F is the bestest Python programmer ever!"
        elif data.command in ["leonard", "leonard^bloom"]:
            msg = "\x02Leonard^Bloom\x0F is the biggest slacker ever!"
        elif data.command in ["groove", "groovedog"]:
            msg = "\x02GrooveDog\x0F is the bestest heh evar!"
        else:
            if not data.args:
                msg = "You use this command to praise certain people. Who they are is a secret."
            else:
                msg = "You're doing it wrong."
            self.connection.reply(data, msg)
            return

        self.connection.say(data.chan, msg)
