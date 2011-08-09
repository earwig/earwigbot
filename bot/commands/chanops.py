# -*- coding: utf-8  -*-

from classes import BaseCommand
import config

class Command(BaseCommand):
    """Voice, devoice, op, or deop users in the channel."""
    name = "chanops"

    def check(self, data):
        commands = ["chanops", "voice", "devoice", "op", "deop"]
        if data.is_command and data.command in commands:
            return True
        return False

    def process(self, data):
        if data.command == "chanops":
            msg = "available commands are !voice, !devoice, !op, and !deop."
            self.connection.reply(data, msg)
            return

        if data.host not in config.irc["permissions"]["admins"]:
            msg = "you must be a bot admin to use this command."
            self.connection.reply(data, msg)
            return

        # If it is just !op/!devoice/whatever without arguments, assume they
        # want to do this to themselves:
        if not data.args:
            target = data.nick
        else:
            target = data.args[0]

        msg = " ".join((data.command, data.chan, target))
        self.connection.say("ChanServ", msg)
