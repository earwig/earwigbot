# -*- coding: utf-8  -*-

import unittest

import support
from commands.test import Command

class TestTest(support.CommandTestCase):

    def setUp(self):
        super(TestTest, self).setUp(Command)

    def test_check(self):
        self.assertFalse(self.command.check(self.make_msg("bloop")))
        self.assertFalse(self.command.check(self.make_join()))

        self.assertTrue(self.command.check(self.make_msg("test")))
        self.assertTrue(self.command.check(self.make_msg("TEST", "foo")))

    def test_process(self):
        def _test():
            self.command.process(self.make_msg("test"))
            self.assertSaidIn(["Hey \x02Foo\x0F!", "'sup \x02Foo\x0F?"])

        for i in xrange(64):
            _test()

if __name__ == "__main__":
    unittest.main(verbosity=2)
