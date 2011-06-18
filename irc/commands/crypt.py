# -*- coding: utf-8  -*-

"""
Cryptography functions (hashing and cyphers) for EarwigBot IRC.
"""

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
                    "Hello!'.")
        else:
            return ("Decrypt any string with a given key using an " + 
                    "implementation of Blowfish, e.g. '!decrypt some_key " + 
                    "762cee8a5239548af18275d6c1184f16'.")

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
                self.connection.reply(data, ("a key was provided, but text " +
                "to {0} was not.").format(data.command))
                return

            try:
                if data.command == "encrypt":
                    result = blowfish.encrypt(key, text)
                else:
                    result = blowfish.decrypt(key, text)
            except blowfish.KeyTooShortError:
                self.connection.reply(data, "key is too short.")
            except blowfish.KeyTooLongError:
                self.connection.reply(data, "key is too long.")
            except blowfish.IncorrectKeyError:
                self.connection.reply(data, "key is incorrect!")
            except blowfish.BadCyphertextError as e:
                self.connection.reply(data, "bad cyphertext: {0}.".format(e))
            else:
                self.connection.reply(data, result)
