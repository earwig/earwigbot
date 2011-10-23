# -*- coding: utf-8  -*-

"""
EarwigBot's Unit Test Support

This module provides some support code for unit tests.

Importing this module will "fix" your path so that EarwigBot code from bot/ can
be imported normally.

CommandTestCase is a subclass of unittest.TestCase that provides setUp() for
creating a fake connection and some other helpful methods. It uses 
FakeConnection, a subclass of classes.Connection, but with an internal string
instead of a socket for data.
"""

from os import path
import re
import sys
from unittest import TestCase

root_dir = path.split(path.dirname(path.abspath(__file__)))[0]
code_dir = path.join(root_dir, "bot")
sys.path.insert(0, code_dir)

from classes import Connection, Data

class CommandTestCase(TestCase):
    re_sender = re.compile(":(.*?)!(.*?)@(.*?)\Z")

    def setUp(self, command):
        self.connection = FakeConnection()
        self.connection.connect()
        self.command = command(self.connection)

    def get_single(self):
        data = self.connection.get().split("\n")
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

class FakeConnection(Connection):
    def connect(self):
        self._buffer = ""

    def close(self):
        pass

    def get(self, size=4096):
        data, self._buffer = self._buffer, ""
        return data

    def send(self, msg):
        self._buffer += msg + "\n"
