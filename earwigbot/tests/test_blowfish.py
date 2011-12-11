# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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
import random
import string

from earwigbot import blowfish

class TestBlowfish(unittest.TestCase):

    def test_key_sizes(self):
        b = blowfish.Blowfish
        e = blowfish.KeyLengthError

        self.assertRaisesRegexp(e, "no key given", b, None)
        self.assertRaisesRegexp(e, "no key given", b, "")
        self.assertRaisesRegexp(e, "at least", b, " " * 3)
        self.assertRaisesRegexp(e, "at least", b, "1234567")
        self.assertRaisesRegexp(e, "less than", b, " " * 57)
        self.assertRaisesRegexp(e, "less than", b, "x" * 60)
        self.assertRaisesRegexp(e, "less than", b, "1" * 128)

        b("These keys should be valid!")
        b("'!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'")
        b(" " * 8)
        b(" " * 56)

    def test_symmetry(self):
        def _test_symmetry():
            key_length = random.randint(8, 56)
            msg_length = random.randint(0, 4096)
            key = "".join([random.choice(chars) for i in xrange(key_length)])
            msg = "".join([random.choice(chars) for i in xrange(msg_length)])
            
            enc = blowfish.encrypt(key, msg)
            dec = blowfish.decrypt(key, enc)
            self.assertEqual(dec, msg)

        chars = string.letters + string.digits + string.punctuation
        for i in xrange(8):
            _test_symmetry()

    def test_encryption(self):
        tests = [
            ("example_key", "Hello, I'm a message!", "8411a21574431176cdff9a549d27962c616014a9fe2a1fe3b0c7a823e8a1e635"),
            ("another random key", "Another random message! :(", "2cdcdf4e53145897ed9d4cc2433aa4bf59b087b14d0ac76a13eff12dec00e60c40857109da3c7bc4"),
            ("HEY LET'S TRY |°|_J|\|C7|_J/-\\710|\|", "Yes, that was my fail attempt at 1337SP33K >_>", "d4901c7c0956da3b9507cd81cd3c880d7cda25ec6c5336deb9280ce67c099eeddf7c7e052f3a946afbd92c32ae0ab8dbdd875bc5a3f0d686")
        ]

        for test in tests:
            self.assertEquals(blowfish.encrypt(test[0], test[1]), test[2])

    def test_decryption(self):
        tests = [
            ("blah blah blah", "ab35274c66bb8b3b03c9bd26ab477f3de06857e1d369ad35", "Blah, blah, blah!"),
            ("random key", "eb2fe950c5c12bca9534ffdd27631f33d3e4bcae53a634b4aaa09f9fe14c4386", "Random message as well!"),
            ("Okay, now I'm just desperate", "0da74e1cec41e8323da93d0c05bcf3919084130cef93021991da174fd97f8e1c9b125ed5263b41a8", "Unit testing is SO FUN ISN'T IT.")
        ]

        for test in tests:
            self.assertEquals(blowfish.decrypt(test[0], test[1]), test[2])

    def test_decryption_exceptions(self):
        d = blowfish.decrypt
        e = blowfish.BlowfishError

        e1 = "could not be decoded"
        e2 = "cannot be broken into 8-byte blocks"
        e3 = "key is incorrect"

        self.assertRaisesRegexp(e, e1, d, "some_key", "arr!")
        self.assertRaisesRegexp(e, e2, d, "some_key", "abcd")
        self.assertRaisesRegexp(e, e3, d, "some_key", "abcdabcdabcdabcd")

if __name__ == "__main__":
    unittest.main(verbosity=2)
