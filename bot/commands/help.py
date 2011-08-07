# -*- coding: utf-8  -*-

from classes import BaseCommand, Data
import commands

class Command(BaseCommand):
    """Generates help information."""
    name = "help"

    def process(self, data):
        self.cmnds = commands.get_all().keys()
        if not data.args:
            self.do_main_help(data)
        else:
            self.do_command_help(data)

    def do_main_help(self, data):
        """Give the user a general help message with a list of all commands."""
        msg = "I am a bot! I have {0} commands loaded: {1}. You can get help for any command with '!help <command>'."
        msg.format(len(self.cmnds), ', '.join(self.cmnds))
        self.connection.reply(data, msg)

    def do_command_help(self, data):
        """Give the user help for a specific command."""
        command = data.args[0]

        # Create a dummy message to test which commands pick up the user's
        # input:
        dummy = Data()
        dummy.command = command.lower()
        dummy.is_command = True

        for cmnd in self.cmnds:
            if cmnd.check(dummy):
                doc = cmnd.__doc__
                if doc:
                    msg = "info for command \x0303{0}\x0301: \"{1}\""
                    msg.format(command, doc)
                    self.connection.reply(data, msg)
                    return
                break

        msg = "sorry, no help for \x0303{0}\x0301.".format(command)
        self.connection.reply(data, msg)
