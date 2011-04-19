# -*- coding: utf-8  -*-

# Voice/devoice/op/deop users in the channel.

from irc.base_command import BaseCommand
from config.irc_config import *

class ChanOps(BaseCommand):
    def get_hook(self):
        return "msg"

    def get_help(self, command):
        action = command.capitalize()
        return "%s users in the channel." % action

    def check(self, data):
        if data.is_command and (data.command == "voice" or data.command == "devoice"
        or data.command == "op" or data.command == "deop"):
            return True
        return False

    def process(self, data):
        if data.host not in ADMINS:
            self.connection.reply(data, "you must be a bot admin to use this command.")
            return

        if not data.args: # if it is just !op/!devoice/whatever without arguments, assume they want to do this to themselves
            target = data.nick
        else:
            target = data.args[0]

        self.connection.say("ChanServ", "%s %s %s" % (data.command, data.chan, target))
