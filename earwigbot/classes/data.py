# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re

__all__ = ["KwargParseException", "Data"]

class KwargParseException(Exception):
    """Couldn't parse a certain keyword argument in self.args, probably because
    it was given incorrectly: e.g., no value (abc), just a value (=xyz), just
    an equal sign (=), instead of the correct (abc=xyz)."""
    pass

class Data(object):
    """Store data from an individual line received on IRC."""
    
    def __init__(self, line):
        self.line = line
        self.chan = self.nick = self.ident = self.host = self.msg = ""

    def parse_args(self):
        """Parse command args from self.msg into self.command and self.args."""
        args = self.msg.strip().split()

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
