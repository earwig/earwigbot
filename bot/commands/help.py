# -*- coding: utf-8  -*-

import re

from classes import BaseCommand, Data
import commands

class Command(BaseCommand):
    """Displays help information."""
    name = "help"

    def process(self, data):
        self.cmnds = commands.get_all()
        if not data.args:
            self.do_main_help(data)
        else:
            self.do_command_help(data)

    def do_main_help(self, data):
        """Give the user a general help message with a list of all commands."""
        msg = "I am a bot! I have {0} commands loaded: {1}. You can get help for any command with '!help <command>'."
        cmnds = self.cmnds.keys()
        cmnds.sort()
        msg = msg.format(len(cmnds), ', '.join(cmnds))
        self.connection.reply(data, msg)

    def do_command_help(self, data):
        """Give the user help for a specific command."""
        command = data.args[0]

        # Create a dummy message to test which commands pick up the user's
        # input:
        dummy = Data("PRIVMSG #fake-channel :Fake messsage!")
        dummy.command = command.lower()
        dummy.is_command = True

        for cmnd in self.cmnds.values():
            if not cmnd.check(dummy):
                continue
            if cmnd.__doc__:
                doc = cmnd.__doc__.replace("\n", "")
                doc = re.sub("\s\s+", " ", doc)
                msg = "info for command \x0303{0}\x0301: \"{1}\""
                self.connection.reply(data, msg.format(command, doc))
                return
            break

        msg = "sorry, no help for \x0303{0}\x0301.".format(command)
        self.connection.reply(data, msg)
