# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from earwigbot.exceptions import KwargParseError

__all__ = ["Data"]

class Data(object):
    """Store data from an individual line received on IRC."""

    def __init__(self, bot, line):
        self.line = line
        self.my_nick = bot.config.irc["frontend"]["nick"].lower()
        self.chan = self.nick = self.ident = self.host = self.msg = ""

    def parse_args(self):
        """Parse command arguments from the message.

        :py:attr:`self.msg <msg>` is converted into the string
        :py:attr:`self.command <command>` and the argument list
        :py:attr:`self.args <args>` if the message starts with a "trigger"
        (``"!"``, ``"."``, or the bot's name); :py:attr:`self.is_command
        <is_command>` will be set to ``True``, and :py:attr:`self.trigger
        <trigger>` will store the trigger string. Otherwise,
        :py:attr:`is_command` will be set to ``False``."""
        args = self.msg.strip().split()

        while "" in args:
            args.remove("")

        # Isolate command arguments:
        self.args = args[1:]
        self.is_command = False  # Is this message a command?
        self.trigger = None  # What triggered this command? (!, ., or our nick)

        try:
            self.command = args[0].lower()
        except IndexError:
            self.command = None
            return

        if self.command.startswith("!") or self.command.startswith("."):
            # e.g. "!command arg1 arg2"
            self.is_command = True
            self.trigger = self.command[0]
            self.command = self.command[1:]  # Strip the "!" or "."
        elif self.command.startswith(self.my_nick):
            # e.g. "EarwigBot, command arg1 arg2"
            self.is_command = True
            self.trigger = self.my_nick
            try:
                self.command = self.args.pop(0).lower()
            except IndexError:
                self.command = ""

    def parse_kwargs(self):
        """Parse keyword arguments embedded in :py:attr:`self.args <args>`.

        Parse a command given as ``"!command key1=value1 key2=value2..."``
        into a dict, :py:attr:`self.kwargs <kwargs>`, like
        ``{'key1': 'value2', 'key2': 'value2'...}``.
        """
        self.kwargs = {}
        for arg in self.args[2:]:
            try:
                key, value = re.findall("^(.*?)\=(.*?)$", arg)[0]
            except IndexError:
                raise KwargParseError(arg)
            if key and value:
                self.kwargs[key] = value
            else:
                raise KwargParseError(arg)
