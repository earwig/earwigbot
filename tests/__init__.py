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

This __init__ file provides some support code for unit tests.

Test cases:
  -- CommandTestCase provides setUp() for creating a fake connection, plus
     some other helpful methods for testing IRC commands.

Fake objects:
  -- FakeBot implements Bot, using the Fake* equivalents of all objects
     whenever possible.
  -- FakeBotConfig implements BotConfig with silent logging.
  -- FakeIRCConnection implements IRCConnection, using an internal string
     buffer for data instead of sending it over a socket.

"""

import logging
from os import path
import re
from threading import Lock
from unittest import TestCase

from earwigbot.bot import Bot
from earwigbot.commands import CommandManager
from earwigbot.config import BotConfig
from earwigbot.irc import IRCConnection, Data
from earwigbot.tasks import TaskManager
from earwigbot.wiki import SitesDB

class CommandTestCase(TestCase):
    re_sender = re.compile(":(.*?)!(.*?)@(.*?)\Z")

    def setUp(self, command):
        self.bot = FakeBot(path.dirname(__file__))
        self.command = command(self.bot)
        self.command.connection = self.connection = self.bot.frontend

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


class FakeBot(Bot):
    def __init__(self, root_dir):
        self.config = FakeBotConfig(root_dir)
        self.logger = logging.getLogger("earwigbot")
        self.commands = CommandManager(self)
        self.tasks = TaskManager(self)
        self.wiki = SitesDB(self)
        self.frontend = FakeIRCConnection(self)
        self.watcher = FakeIRCConnection(self)

        self.component_lock = Lock()
        self._keep_looping = True


class FakeBotConfig(BotConfig):
    def _setup_logging(self):
        logger = logging.getLogger("earwigbot")
        logger.addHandler(logging.NullHandler())


class FakeIRCConnection(IRCConnection):
    def __init__(self, bot):
        self.bot = bot
        self._is_running = False
        self._connect()

    def _connect(self):
        self._buffer = ""

    def _close(self):
        self._buffer = ""

    def _get(self, size=4096):
        data, self._buffer = self._buffer, ""
        return data

    def _send(self, msg):
        self._buffer += msg + "\n"
