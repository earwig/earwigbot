# -*- coding: utf-8  -*-

# A class to store data from an individual line received on IRC.

class Data(object):
    def __init__(self):
        """store data from an individual line received on IRC"""
        self.chan = str()
        self.nick = str()
        self.ident = str()
        self.host = str()
        self.msg = str()

    def parse_args(self):
        """parse command arguments from self.msg into self.command and self.args"""
        args = self.msg.strip().split(' ') # strip out extra whitespace and split the message into a list
        while '' in args: # remove any empty arguments
            args.remove('')

        self.args = args[1:] # the command arguments
        self.is_command = False # whether this is a real command or not

        try:
            self.command = args[0] # the command itself
        except IndexError:
            self.command = None

        try:
            if self.command.startswith('!') or self.command.startswith('.'):
                self.is_command = True
                self.command = self.command[1:] # strip '!' or '.'
        except AttributeError:
            pass
