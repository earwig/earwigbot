# -*- coding: utf-8  -*-

# Generates help information.

from irc.classes import BaseCommand, Data
from irc import command_handler

class Help(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Generates help information."

    def check(self, data):
        if data.is_command and data.command == "help":
            return True
        return False

    def process(self, data):
        if not data.args:
            self.do_general_help(data)
        else:
            if data.args[0] == "list":
                self.do_list_help(data)
            else:
                self.do_command_help(data)

    def do_general_help(self, data):
        self.connection.reply(data, "I am a bot! You can get help for any command with '!help <command>', or a list of all loaded modules with '!help list'.")

    def do_list_help(self, data):
        commands = command_handler.get_commands()
        cmnds = map(lambda c: c.__class__.__name__, commands)
        pretty_cmnds = ', '.join(cmnds)
        self.connection.reply(data, "%s command classes loaded: %s." % (len(cmnds), pretty_cmnds))

    def do_command_help(self, data):
        command = data.args[0]
        commands = command_handler.get_commands()

        dummy = Data() # dummy message to test which command classes pick up this command
        dummy.command = command.lower() # lowercase command name
        dummy.is_command = True

        for cmnd in commands:
            if cmnd.check(dummy):
                help = cmnd.get_help(command)
                break

        try:
            self.connection.reply(data, "info for command \x0303%s\x0301: \"%s\"" % (command, help))
        except UnboundLocalError:
            self.connection.reply(data, "sorry, no help for \x0303%s\x0301." % command)
