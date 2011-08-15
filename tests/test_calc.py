# -*- coding: utf-8  -*-

import unittest

import support
from commands.calc import Command

class TestCalc(support.CommandTestCase):

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
