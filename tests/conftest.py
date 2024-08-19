# Copyright (C) 2009-2024 Ben Kurtovic <ben.kurtovic@gmail.com>
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

This conftest provides some support code for unit tests.

Fixtures:
  -- ``command`` creates a mock connection and provides some helpful methods for
     testing IRC commands.

Mock objects:
  -- ``MockBot`` implements ``Bot``, using the ``Mock`` equivalents of all objects
     whenever possible.
  -- ``MockBotConfig`` implements ``BotConfig`` with silent logging.
  -- ``MockIRCConnection`` implements ``IRCConnection``, using an internal string
     buffer for data instead of sending it over a socket.
"""

import logging
import os.path
import re
from collections.abc import Iterable, Sequence
from threading import Lock

import pytest
from earwigbot.bot import Bot
from earwigbot.commands import Command
from earwigbot.config import BotConfig
from earwigbot.irc import Data, IRCConnection
from earwigbot.managers import CommandManager, TaskManager
from earwigbot.wiki import SitesDB


@pytest.fixture
def command():
    return MockCommand()


class MockCommand:
    re_sender = re.compile(r":(.*?)!(.*?)@(.*?)\Z")

    def setup(self, command: type[Command]) -> None:
        self.bot = MockBot(os.path.dirname(__file__))
        self.command = command(self.bot)

    def get_single(self) -> str:
        data = self.bot.frontend._get().split("\n")
        line = data.pop(0)
        for remaining in data[1:]:
            self.bot.frontend._send(remaining)
        return line

    def assert_sent(self, msg: str) -> None:
        line = self.get_single()
        assert line == msg

    def assert_sent_in(self, msgs: Iterable[str]) -> None:
        line = self.get_single()
        assert line in msgs

    def assert_said(self, msg: str) -> None:
        self.assert_sent(f"PRIVMSG #channel :{msg}")

    def assert_said_in(self, msgs: Iterable[str]) -> None:
        msgs = [f"PRIVMSG #channel :{msg}" for msg in msgs]
        self.assert_sent_in(msgs)

    def assert_reply(self, msg: str) -> None:
        self.assert_said(f"\x02Foo\x0f: {msg}")

    def assert_reply_in(self, msgs: Iterable[str]) -> None:
        msgs = [f"\x02Foo\x0f: {msg}" for msg in msgs]
        self.assert_said_in(msgs)

    def _make(self, line: Sequence[str]) -> Data:
        return Data(self.bot.frontend.nick, line, line[1])

    def make_msg(self, command, *args):
        line = f":Foo!bar@example.com PRIVMSG #channel :!{command}"
        line = line.strip().split()
        line.extend(args)
        return self._make(line)

    def make_join(self):
        line = ":Foo!bar@example.com JOIN :#channel".strip().split()
        return self._make(line)


class MockBot(Bot):
    def __init__(self, root_dir: str, level=logging.INFO) -> None:
        self.config = MockBotConfig(self, root_dir, level)
        self.logger = logging.getLogger("earwigbot")
        self.commands = CommandManager(self)
        self.tasks = TaskManager(self)
        self.wiki = SitesDB(self)
        self.frontend = MockIRCConnection(self)
        self.watcher = MockIRCConnection(self)

        self.component_lock = Lock()
        self._keep_looping = True


class MockBotConfig(BotConfig):
    def _setup_logging(self) -> None:
        logger = logging.getLogger("earwigbot")
        logger.addHandler(logging.NullHandler())


class MockIRCConnection(IRCConnection):
    def __init__(self, bot: MockBot) -> None:
        super().__init__(
            "localhost",
            6667,
            "MockBot",
            "mock",
            "Mock Bot",
            bot.logger.getChild("mock"),
        )
        self._buffer = ""

    def _connect(self) -> None:
        self._buffer = ""

    def _close(self) -> None:
        self._buffer = ""

    def _get(self, size: int = 4096) -> str:
        data, self._buffer = self._buffer, ""
        return data

    def _send(self, msg: str, hidelog: bool = False) -> None:
        self._buffer += msg + "\n"
