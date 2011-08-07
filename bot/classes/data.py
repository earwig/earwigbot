# -*- coding: utf-8  -*-

# A class to store data from an individual line received on IRC.

import re

class KwargParseException(Exception):
    """Couldn't parse a certain keyword argument in self.args, probably because
    it was given incorrectly: e.g., no value (abc), just a value (=xyz), just
    an equal sign (=), instead of the correct (abc=xyz)."""
    pass

class Data(object):
    def __init__(self, line):
        """Store data from an individual line received on IRC."""
        self.line = line
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
                self.command = self.command.lower() # lowercase command name
        except AttributeError:
            pass

    def parse_kwargs(self):
        """parse command arguments from self.args, given as !command key1=value1 key2=value2..., into a dict self.kwargs: {'key1': 'value2', 'key2': 'value2'...}"""
        self.kwargs = {}
        for arg in self.args[2:]:
            try:
                key, value = re.findall("^(.*?)\=(.*?)$", arg)[0]
            except IndexError:
                raise KwargParseException(arg)
            if not key or not value:
                raise KwargParseException(arg)
            self.kwargs[key] = value
