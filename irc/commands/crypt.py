# -*- coding: utf-8  -*-

# Cryptography functions (hashing and cyphers).

import hashlib

from irc.base_command import BaseCommand

class Cryptography(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        if command == "hash":
            return ("Return the hash of a string using a given algorithm, " +
                    "e.g. '!hash sha512 Hello world!'.")
        else:
            return ("{0} a string with a given key using a given algorithm, " +
                    "e.g. '!{1} blowfish some_key Hello world!'.").format(
                    command.capitalize(), command)

    def check(self, data):
        if data.is_command and data.command in ["hash", "encrypt", "decrypt"]:
            return True
        return False

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "what do you want me to do?")
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo in hashlib.algorithms:
                string = ' '.join(data.args[1:])
                result = eval("hashlib.{0}(string)".format(algo)).hexdigest()
                self.connection.reply(data, result)
            else:
                self.connection.reply(data, "unknown algorithm: {0}".format(
                        algo))

        else:
            self.connection.reply(data, "not implemented yet!")
