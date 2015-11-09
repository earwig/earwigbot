# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

import platform
import time

from earwigbot import __version__
from earwigbot.commands import Command

class CTCP(Command):
    """Not an actual command; this module implements responses to the CTCP
    requests PING, TIME, and VERSION."""
    name = "ctcp"
    hooks = ["msg_private"]

    def check(self, data):
        if data.is_command and data.command == "ctcp":
            return True

        commands = ["PING", "TIME", "VERSION"]
        msg = data.line[3]
        if msg[:2] == ":\x01" and msg[2:].rstrip("\x01") in commands:
            return True
        return False

    def process(self, data):
        if data.is_command:
            return

        target = data.nick
        command = data.line[3][1:].strip("\x01")

        if command == "PING":
            msg = " ".join(data.line[4:])
            if msg:
                self.notice(target, "\x01PING {0}\x01".format(msg))
            else:
                self.notice(target, "\x01PING\x01")

        elif command == "TIME":
            ts = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime())
            self.notice(target, "\x01TIME {0}\x01".format(ts))

        elif command == "VERSION":
            default = "EarwigBot - $1 - Python/$2 https://github.com/earwig/earwigbot"
            vers = self.config.irc.get("version", default)
            vers = vers.replace("$1", __version__)
            vers = vers.replace("$2", platform.python_version())
            self.notice(target, "\x01VERSION {0}\x01".format(vers))
