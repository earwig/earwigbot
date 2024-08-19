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

from conftest import MockCommand
from earwigbot.commands.test import Test


def test_check(command: MockCommand):
    command.setup(Test)

    assert command.command.check(command.make_msg("bloop")) is False
    assert command.command.check(command.make_join()) is False

    assert command.command.check(command.make_msg("test")) is True
    assert command.command.check(command.make_msg("TEST", "foo")) is True


def test_process(command: MockCommand):
    command.setup(Test)

    for i in range(64):
        command.command.process(command.make_msg("test"))
        command.assert_said_in(["Hey \x02Foo\x0f!", "'Sup \x02Foo\x0f?"])
