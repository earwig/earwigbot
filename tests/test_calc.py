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

import pytest

from conftest import MockCommand
from earwigbot.commands.calc import Calc


def test_check(command: MockCommand):
    command.setup(Calc)

    assert command.command.check(command.make_msg("bloop")) is False
    assert command.command.check(command.make_join()) is False

    assert command.command.check(command.make_msg("calc")) is True
    assert command.command.check(command.make_msg("CALC", "foo")) is True


def test_ignore_empty(command: MockCommand):
    command.setup(Calc)

    command.command.process(command.make_msg("calc"))
    command.assert_reply("What do you want me to calculate?")


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("2 + 2", "2 + 2 = 4"),
        ("13 * 5", "13 * 5 = 65"),
        ("80 / 42", "80 / 42 = 40/21 (approx. 1.9047619047619048)"),
        ("2/0", "2/0 = undef"),
        ("π", "π = 3.141592653589793238"),
    ],
)
def test_math(command: MockCommand, expr: str, expected: str):
    command.setup(Calc)

    q = expr.strip().split()
    command.command.process(command.make_msg("calc", *q))
    command.assert_reply(expected)
