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

"""
EarwigBot's Unit Tests

This module __init__ file provides some support code for unit tests.

CommandTestCase is a subclass of unittest.TestCase that provides setUp() for
creating a fake connection and some other helpful methods. It uses 
FakeConnection, a subclass of classes.Connection, but with an internal string
instead of a socket for data.
"""

import re
from unittest import TestCase

from earwigbot.irc import IRCConnection, Data

class CommandTestCase(TestCase):
    re_sender = re.compile(":(.*?)!(.*?)@(.*?)\Z")

    def setUp(self, command):
        self.connection = FakeConnection()
        self.connection._connect()
        self.command = command(self.connection)

    def get_single(self):
        data = self.connection._get().split("\n")
        line = data.pop(0)
        for remaining in data[1:]:
            self.connection.send(remaining)
        return line

    def assertSent(self, msg):
        line = self.get_single()
        self.assertEqual(line, msg)

    def assertSentIn(self, msgs):
        line = self.get_single()
        self.assertIn(line, msgs)

    def assertSaid(self, msg):
        self.assertSent("PRIVMSG #channel :{0}".format(msg))

    def assertSaidIn(self, msgs):
        msgs = ["PRIVMSG #channel :{0}".format(msg) for msg in msgs]
        self.assertSentIn(msgs)

    def assertReply(self, msg):
        self.assertSaid("\x02Foo\x0F: {0}".format(msg))

    def assertReplyIn(self, msgs):
        msgs = ["\x02Foo\x0F: {0}".format(msg) for msg in msgs]
        self.assertSaidIn(msgs)

    def maker(self, line, chan, msg=None):
        data = Data(line)
        data.nick, data.ident, data.host = self.re_sender.findall(line[0])[0]
        if msg is not None:
            data.msg = msg
        data.chan = chan
        data.parse_args()
        return data

    def make_msg(self, command, *args):
        line = ":Foo!bar@example.com PRIVMSG #channel :!{0}".format(command)
        line = line.strip().split()
        line.extend(args)
        return self.maker(line, line[2], " ".join(line[3:])[1:])

    def make_join(self):
        line = ":Foo!bar@example.com JOIN :#channel".strip().split()
        return self.maker(line, line[2][1:])

class FakeConnection(IRCConnection):
    def __init__(self):
        pass

    def _connect(self):
        self._buffer = ""

    def _close(self):
        pass

    def _get(self, size=4096):
        data, self._buffer = self._buffer, ""
        return data

    def _send(self, msg):
        self._buffer += msg + "\n"
