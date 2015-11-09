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

import hashlib

from earwigbot import importer
from earwigbot.commands import Command

Blowfish = importer.new("Crypto.Cipher.Blowfish")

class Crypt(Command):
    """Provides hash functions with !hash (!hash list for supported algorithms)
    and Blowfish encryption with !encrypt and !decrypt."""
    name = "crypt"
    commands = ["crypt", "hash", "encrypt", "decrypt"]

    def process(self, data):
        if data.command == "crypt":
            msg = "Available commands are !hash, !encrypt, and !decrypt."
            self.reply(data, msg)
            return

        if not data.args:
            msg = "What do you want me to {0}?".format(data.command)
            self.reply(data, msg)
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo == "list":
                algos = ', '.join(hashlib.algorithms)
                msg = algos.join(("Supported algorithms: ", "."))
                self.reply(data, msg)
            elif algo in hashlib.algorithms:
                string = ' '.join(data.args[1:])
                result = getattr(hashlib, algo)(string).hexdigest()
                self.reply(data, result)
            else:
                msg = "Unknown algorithm: '{0}'.".format(algo)
                self.reply(data, msg)

        else:
            key = data.args[0]
            text = " ".join(data.args[1:])

            if not text:
                msg = "A key was provided, but text to {0} was not."
                self.reply(data, msg.format(data.command))
                return

            try:
                cipher = Blowfish.new(hashlib.sha256(key).digest())
            except ImportError:
                msg = "This command requires the 'pycrypto' package: https://www.dlitz.net/software/pycrypto/"
                self.reply(data, msg)
                return

            try:
                if data.command == "encrypt":
                    if len(text) % 8:
                        pad = 8 - len(text) % 8
                        text = text.ljust(len(text) + pad, "\x00")
                    self.reply(data, cipher.encrypt(text).encode("hex"))
                else:
                    self.reply(data, cipher.decrypt(text.decode("hex")))
            except (ValueError, TypeError) as error:
                self.reply(data, error.message)
