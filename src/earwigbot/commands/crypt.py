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

import base64
import hashlib
import os

from earwigbot.commands import Command


class Crypt(Command):
    """Provides hash functions with !hash (!hash list for supported algorithms)
    and basic encryption with !encrypt and !decrypt."""

    name = "crypt"
    commands = ["crypt", "hash", "encrypt", "decrypt"]

    def process(self, data):
        if data.command == "crypt":
            msg = "Available commands are !hash, !encrypt, and !decrypt."
            self.reply(data, msg)
            return

        if not data.args:
            msg = f"What do you want me to {data.command}?"
            self.reply(data, msg)
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo == "list":
                algos = ", ".join(hashlib.algorithms_available)
                msg = algos.join(("Supported algorithms: ", "."))
                self.reply(data, msg)
            elif algo in hashlib.algorithms_available:
                string = " ".join(data.args[1:])
                result = getattr(hashlib, algo)(string.encode()).hexdigest()
                self.reply(data, result)
            else:
                msg = f"Unknown algorithm: '{algo}'."
                self.reply(data, msg)

        else:
            key = data.args[0]
            text = " ".join(data.args[1:])
            saltlen = 16

            if not text:
                msg = "A key was provided, but text to {0} was not."
                self.reply(data, msg.format(data.command))
                return

            try:
                from cryptography import fernet
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.kdf import pbkdf2
            except ModuleNotFoundError:
                self.reply(
                    data,
                    "This command requires the 'cryptography' package: https://cryptography.io/",
                )
                return

            try:
                if data.command == "encrypt":
                    salt = os.urandom(saltlen)
                    kdf = pbkdf2.PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    f = fernet.Fernet(
                        base64.urlsafe_b64encode(kdf.derive(key.encode()))
                    )
                    ciphertext = f.encrypt(text.encode())
                    self.reply(data, base64.b64encode(salt + ciphertext).decode())
                else:
                    if len(text) < saltlen:
                        raise ValueError("Ciphertext is too short")
                    raw = base64.b64decode(text)
                    salt, ciphertext = raw[:saltlen], raw[saltlen:]
                    kdf = pbkdf2.PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    f = fernet.Fernet(
                        base64.urlsafe_b64encode(kdf.derive(key.encode()))
                    )
                    self.reply(data, f.decrypt(ciphertext).decode())
            except Exception as error:
                self.reply(data, f"{type(error).__name__}: {str(error)}")
