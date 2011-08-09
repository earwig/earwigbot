# -*- coding: utf-8  -*-

import hashlib

from classes import BaseCommand
import blowfish

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
            self.connection.reply(data, msg)
            return

        if not data.args:
            msg = "what do you want me to {0}?".format(data.command)
            self.connection.reply(data, msg)
            return

        if data.command == "hash":
            algo = data.args[0]
            if algo == "list":
                algos = ', '.join(hashlib.algorithms)
                msg = algos.join(("supported algorithms: ", "."))
                self.connection.reply(data, msg)
            elif algo in hashlib.algorithms:
                string = ' '.join(data.args[1:])
                result = getattr(hashlib, algo)(string).hexdigest()
                self.connection.reply(data, result)
            else:
                msg = "unknown algorithm: '{0}'.".format(algo)
                self.connection.reply(data, msg)

        else:
            key = data.args[0]
            text = ' '.join(data.args[1:])

            if not text:
                msg = "a key was provided, but text to {0} was not."
                self.connection.reply(data, msg.format(data.command))
                return

            try:
                if data.command == "encrypt":
                    self.connection.reply(data, blowfish.encrypt(key, text))
                else:
                    self.connection.reply(data, blowfish.decrypt(key, text))
            except blowfish.BlowfishError as error:
                msg = "{0}: {1}.".format(error.__class__.__name__, error)
                self.connection.reply(data, msg)
