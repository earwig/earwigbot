# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

import hashlib

from earwigbot import blowfish
from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Provides hash functions with !hash (!hash list for supported algorithms)
    and blowfish encryption with !encrypt and !decrypt."""
    name = "crypt"

    def check(self, data):
        commands = ["crypt", "hash", "encrypt", "decrypt"]
        if data.is_command and data.command in commands:
            return True
        return False

    def process(self, data):
        if data.command == "crypt":
            msg = "available commands are !hash, !encrypt, and !decrypt."
            self.reply(data, msg)
            return

        if not data.args:
            msg = "what do you want me to {0}?".format(data.command)
            self.reply(data, msg)
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo == "list":
                algos = ', '.join(hashlib.algorithms)
                msg = algos.join(("supported algorithms: ", "."))
                self.reply(data, msg)
            elif algo in hashlib.algorithms:
                string = ' '.join(data.args[1:])
                result = getattr(hashlib, algo)(string).hexdigest()
                self.reply(data, result)
            else:
                msg = "unknown algorithm: '{0}'.".format(algo)
                self.reply(data, msg)

        else:
            key = data.args[0]
            text = ' '.join(data.args[1:])

            if not text:
                msg = "a key was provided, but text to {0} was not."
                self.reply(data, msg.format(data.command))
                return

            try:
                if data.command == "encrypt":
                    self.reply(data, blowfish.encrypt(key, text))
                else:
                    self.reply(data, blowfish.decrypt(key, text))
            except blowfish.BlowfishError as error:
                msg = "{0}: {1}.".format(error.__class__.__name__, error)
                self.reply(data, msg)
