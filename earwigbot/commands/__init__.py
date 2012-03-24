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

"""
EarwigBot's IRC Command Manager

This package provides the IRC "commands" used by the bot's front-end component.
This module contains the BaseCommand class (import with
`from earwigbot.commands import BaseCommand`) and an internal _CommandManager
class. This can be accessed through the singleton `command_manager`.
"""

import logging
import os
import sys

from earwigbot.config import config

__all__ = ["BaseCommand", "command_manager"]

class BaseCommand(object):
    """A base class for commands on IRC.

    This docstring is reported to the user when they use !help <command>.
    """
    # This is the command's name, as reported to the user when they use !help:
    name = None

    # Hooks are "msg", "msg_private", "msg_public", and "join". "msg" is the
    # default behavior; if you wish to override that, change the value in your
    # command subclass:
    hooks = ["msg"]

    def __init__(self, connection):
        """Constructor for new commands.

        This is called once when the command is loaded (from
        commands._load_command()). `connection` is a Connection object,
        allowing us to do self.connection.say(), self.connection.send(), etc,
        from within a method.
        """
        self.connection = connection
        logger_name = ".".join(("earwigbot", "commands", self.name))
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)

    def check(self, data):
        """Returns whether this command should be called in response to 'data'.

        Given a Data() instance, return True if we should respond to this
        activity, or False if we should ignore it or it doesn't apply to us.

        Most commands return True if data.command == self.name, otherwise they
        return False. This is the default behavior of check(); you need only
        override it if you wish to change that.
        """
        if data.is_command and data.command == self.name:
            return True
        return False

    def process(self, data):
        """Main entry point for doing a command.

        Handle an activity (usually a message) on IRC. At this point, thanks
        to self.check() which is called automatically by the command handler,
        we know this is something we should respond to, so (usually) something
        like 'if data.command != "command_name": return' is unnecessary.
        """
        pass


class _CommandManager(object):
    def __init__(self):
        self.logger = logging.getLogger("earwigbot.tasks")
        self._base_dir = os.path.dirname(os.path.abspath(__file__))
        self._connection = None
        self._commands = {}

    def _load_command(self, filename):
        """Load a specific command from a module, identified by filename.

        Given a Connection object and a filename, we'll first try to import
        it, and if that works, make an instance of the 'Command' class inside
        (assuming it is an instance of BaseCommand), add it to self._commands,
        and log the addition. Any problems along the way will either be
        ignored or logged.
        """
        # Strip .py from the filename's end and join with our package name:
        name = ".".join(("commands", filename[:-3]))
        try:
             __import__(name)
        except:
            self.logger.exception("Couldn't load file {0}".format(filename))
            return

        try:
            command = sys.modules[name].Command(self._connection)
        except AttributeError:
            return  # No command in this module
        if not isinstance(command, BaseCommand):
            return

        self._commands[command.name] = command
        self.logger.debug("Added command {0}".format(command.name))

    def load(self, connection):
        """Load all valid commands into self._commands.

        `connection` is a Connection object that is given to each command's
        constructor.
        """
        self._connection = connection

        files = os.listdir(self._base_dir)
        files.sort()
        for filename in files:
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            self._load_command(filename)

        msg = "Found {0} commands: {1}"
        commands = ", ".join(self._commands.keys())
        self.logger.info(msg.format(len(self._commands), commands))

    def get_all(self):
        """Return our dict of all loaded commands."""
        return self._commands

    def check(self, hook, data):
        """Given an IRC event, check if there's anything we can respond to."""
        # Parse command arguments into data.command and data.args:
        data.parse_args()
        for command in self._commands.values():
            if hook in command.hooks:
                if command.check(data):
                    try:
                        command.process(data)
                    except Exception:
                        e = "Error executing command '{0}'"
                        self.logger.exception(e.format(data.command))
                    break


command_manager = _CommandManager()
