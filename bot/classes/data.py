# -*- coding: utf-8  -*-

import re

class KwargParseException(Exception):
    """Couldn't parse a certain keyword argument in self.args, probably because
    it was given incorrectly: e.g., no value (abc), just a value (=xyz), just
    an equal sign (=), instead of the correct (abc=xyz)."""
    pass

class Data(object):
    """Store data from an individual line received on IRC."""
    
    def __init__(self, line):
        self.line = line
        self.chan = str()
        self.nick = str()
        self.ident = str()
        self.host = str()
        self.msg = str()

    def parse_args(self):
        """Parse command args from self.msg into self.command and self.args."""
        args = self.msg.strip().split(" ")

        while "" in args:
            args.remove("")

        # Isolate command arguments:
        self.args = args[1:]
        self.is_command = False  # is this message a command?

        try:
            self.command = args[0]
        except IndexError:
            self.command = None

        try:
            if self.command.startswith('!') or self.command.startswith('.'):
                self.is_command = True
                self.command = self.command[1:]  # Strip the '!' or '.'
                self.command = self.command.lower()
        except AttributeError:
            pass

    def parse_kwargs(self):
        """Parse keyword arguments embedded in self.args.
        
        Parse a command given as "!command key1=value1 key2=value2..." into a
        dict, self.kwargs, like {'key1': 'value2', 'key2': 'value2'...}.
        """
        self.kwargs = {}
        for arg in self.args[2:]:
            try:
                key, value = re.findall("^(.*?)\=(.*?)$", arg)[0]
            except IndexError:
                raise KwargParseException(arg)
            if key and value:
                self.kwargs[key] = value
            else:
                raise KwargParseException(arg)
