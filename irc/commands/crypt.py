# -*- coding: utf-8  -*-

# Cryptography functions (hashing and cyphers).

import hashlib

from irc.base_command import BaseCommand
from lib import blowfish

class Cryptography(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        if command == "hash":
            return ("Return the hash of a string using a given algorithm, " +
                    "e.g. '!hash sha512 Hello world!'. Use '!hash list' for " +
                    "a list of supported algorithms.")
        elif command == "encrypt":
            return ("Encrypt any string with a given key using an " + 
                    "implementation of Blowfish, e.g. '!encrypt some_key " + 
                    "Hello world!'.")
        else:
            return ("Decrypt a string with a given key using a given " +
                    "algorithm, e.g. '!decrypt blowfish some_key Hello " +
                    "world!'.")

    def check(self, data):
        if data.is_command and data.command in ["hash", "encrypt", "decrypt"]:
            return True
        return False

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "what do you want me to {0}?".format(
                    data.command))
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo == "list":
                algos = ', '.join(hashlib.algorithms)
                self.connection.reply(data, "supported algorithms: " + algos +
                        ".")
            elif algo in hashlib.algorithms:
                string = ' '.join(data.args[1:])
                result = eval("hashlib.{0}(string)".format(algo)).hexdigest()
                self.connection.reply(data, result)
            else:
                self.connection.reply(data, "unknown algorithm: '{0}'.".format(
                        algo))

        else:
            key = data.args[0]
            text = ' '.join(data.args[1:])
            if not text:
                self.connection.reply(data, "that's a key, yes, but what do " +
                        " you want me to {0}?".format(data.command))
                return
            if data.command == "encrypt":
                self.connection.reply(data, blowfish.encrypt(key, text))
            else:
                self.connection.reply(data, blowfish.decrypt(key, text))
