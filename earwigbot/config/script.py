# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

from getpass import getpass
import re

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import yaml
except ImportError:
    yaml = None

__all__ = ["ConfigScript"]

class ConfigScript(object):
    """A script to guide a user through the creation of a new config file."""
    BCRYPT_ROUNDS = 12

    def __init__(self, config):
        self.config = config
        self.data = {}

    def _prnt(self, msg):
        pass

    def _ask_bool(self, text, default=True):
        pass

    def make_new(self):
        """Make a new config file based on the user's input."""
        print
        self.data["metadata"] = {"version": 1}
        self._print("""I can encrypt passwords stored in your config file in
                       addition to preventing other users on your system from
                       reading the file. Encryption is recommended is the bot
                       is to run on a public computer like the Toolserver, but
                       otherwise the need to enter a key everytime you start
                       the bot may be annoying.""")
        if self._ask_bool("Encrypt stored passwords?"):
            self.data["metadata"]["encryptPasswords"] = True
            key = getpass("> Enter an encryption key: ")
            print "Running {0} rounds of bcrypt...".format(self.BCRYPT_ROUNDS),
            signature = bcrypt.hashpw(key, bcrypt.gensalt(self.BCRYPT_ROUNDS))
            self.data["metadata"]["signature"] = signature
            print " done."
        else:
            self.data["metadata"]["encryptPasswords"] = False

        self._print("""The bot can temporarily store its logs in the logs/
                       subdirectory. Error logs are kept for a month whereas
                       normal logs are kept for a week. If you disable this,
                       the bot will still print logs to stdout.""")
        question = "Enable logging?"
        self.data["metadata"]["enableLogging"] = self._ask_bool(question)
