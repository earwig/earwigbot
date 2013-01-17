# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2013 Ben Kurtovic <ben.kurtovic@verizon.net>
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

import unittest

from earwigbot.commands.calc import Command
from tests import CommandTestCase

class TestCalc(CommandTestCase):

    def setUp(self):
        super(TestCalc, self).setUp(Command)

    def test_check(self):
        self.assertFalse(self.command.check(self.make_msg("bloop")))
        self.assertFalse(self.command.check(self.make_join()))

        self.assertTrue(self.command.check(self.make_msg("calc")))
        self.assertTrue(self.command.check(self.make_msg("CALC", "foo")))

    def test_ignore_empty(self):
        self.command.process(self.make_msg("calc"))
        self.assertReply("what do you want me to calculate?")

    def test_maths(self):
        tests = [
            ("2 + 2", "2 + 2 = 4"),
            ("13 * 5", "13 * 5 = 65"),
            ("80 / 42", "80 / 42 = 40/21 (approx. 1.9047619047619047)"),
            ("2/0", "2/0 = undef"),
            ("π", "π = 3.141592653589793238"),
        ]

        for test in tests:
            q = test[0].strip().split()
            self.command.process(self.make_msg("calc", *q))
            self.assertReply(test[1])

if __name__ == "__main__":
    unittest.main(verbosity=2)
