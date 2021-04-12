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

import unittest

from earwigbot.commands.test import Command
from tests import CommandTestCase

class TestTest(CommandTestCase):

    def setUp(self):
        super().setUp(Command)

    def test_check(self):
        self.assertFalse(self.command.check(self.make_msg("bloop")))
        self.assertFalse(self.command.check(self.make_join()))

        self.assertTrue(self.command.check(self.make_msg("test")))
        self.assertTrue(self.command.check(self.make_msg("TEST", "foo")))

    def test_process(self):
        def test():
            self.command.process(self.make_msg("test"))
            self.assertSaidIn(["Hey \x02Foo\x0F!", "'sup \x02Foo\x0F?"])

        for i in range(64):
            test()

if __name__ == "__main__":
    unittest.main(verbosity=2)
