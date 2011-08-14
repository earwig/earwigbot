# -*- coding: utf-8  -*-

import platform
import time

from classes import BaseCommand
import config

class Command(BaseCommand):
    """Not an actual command, this module is used to respond to the CTCP
    commands PING, TIME, and VERSION."""
    name = "ctcp"
    hooks = ["msg_private"]

    def check(self, data):
        if data.is_command and data.command == "ctcp":
            return True

        commands = ["PING", "TIME", "VERSION"]
        msg = data.line[3]
        if msg[:2] == ":\x01" and msg[2:].rstrip("\x01") in commands:
            return True
        return False

    def process(self, data):
        if data.is_command:
            return

        target = data.nick
        command = data.line[3][1:].strip("\x01")

        if command == "PING":
            msg = " ".join(data.line[4:])
            if msg:
                self.connection.notice(target, "\x01PING {0}\x01".format(msg))
            else:
                self.connection.notice(target, "\x01PING\x01")

        elif command == "TIME":
            ts = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime())
            self.connection.notice(target, "\x01TIME {0}\x01".format(ts))

        elif command == "VERSION":
            default = "EarwigBot - 0.1-dev - Python/$1 https://github.com/earwig/earwigbot"
            vers = config.metadata.get("ircVersion", default)
            vers = vers.replace("$1", platform.python_version())
            self.connection.notice(target, "\x01VERSION {0}\x01".format(vers))
