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
        self.command.process(self.make_msg("test"))

        msgs = ["PRIVMSG #channel :Hey \x02Foo\x0F!",
                "PRIVMSG #channel :'sup \x02Foo\x0F?"]
        self.assertSentIn(msgs)

if __name__ == "__main__":
    unittest.main(verbosity=2)
