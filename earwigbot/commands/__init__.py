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
`from earwigbot.commands import BaseCommand`) and an internal CommandManager
class. This can be accessed through `bot.commands`.
"""

import imp
from os import listdir, path
from re import sub
from threading import Lock

__all__ = ["BaseCommand", "CommandManager"]

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

    def __init__(self, bot):
        """Constructor for new commands.

        This is called once when the command is loaded (from
        commands._load_command()). `bot` is out base Bot object. Generally you
        shouldn't need to override this; if you do, call
        super(Command, self).__init__() first.
        """
        self.bot = bot
        self.config = bot.config
        self.logger = bot.commands.getLogger(self.name)

    def _wrap_process(self, data):
        """Make a quick connection alias and then process() the message."""
        self.connection = self.bot.frontend
        self.process(data)

    def check(self, data):
        """Return whether this command should be called in response to 'data'.

        Given a Data() instance, return True if we should respond to this
        activity, or False if we should ignore it or it doesn't apply to us.

        Most commands return True if data.command == self.name, otherwise they
        return False. This is the default behavior of check(); you need only
        override it if you wish to change that.
        """
        return data.is_command and data.command == self.name

    def process(self, data):
        """Main entry point for doing a command.

        Handle an activity (usually a message) on IRC. At this point, thanks
        to self.check() which is called automatically by the command handler,
        we know this is something we should respond to, so something like
        `if data.command != "command_name": return` is usually unnecessary.
        Note that 
        """
        pass


class CommandManager(object):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getLogger("commands")
        self._commands = {}
        self._command_access_lock = Lock()

    def _load_command(self, name, path):
        """Load a specific command from a module, identified by name and path.

        We'll first try to import it using imp magic, and if that works, make
        an instance of the 'Command' class inside (assuming it is an instance
        of BaseCommand), add it to self._commands, and log the addition. Any
        problems along the way will either be ignored or logged.
        """
        f, path, desc = imp.find_module(name, [path])
        try:
             module = imp.load_module(name, f, path, desc)
        except Exception:
            e = "Couldn't load module {0} from {1}"
            self.logger.exception(e.format(name, path))
            return
        finally:
            f.close()

        try:
            command_class = module.Command
        except AttributeError:
            return  # No command in this module
        try:
            command = command_class(self.bot)
        except Exception:
            e = "Error initializing Command() class in {0} (from {1})"
            self.logger.exception(e.format(name, path))
            return
        if not isinstance(command, BaseCommand):
            return

        self._commands[command.name] = command
        self.logger.debug("Added command {0}".format(command.name))

    def load(self):
        """Load (or reload) all valid commands into self._commands."""
        with self._command_access_lock:
            self._commands.clear()
            dirs = [path.join(path.dirname(__file__), "commands"),
                    path.join(self.bot.config.root_dir, "commands")]
            for dir in dirs:
                files = listdir(dir)
                files = [sub("\.pyc?$", "", f) for f in files if f[0] != "_"]
                files = list(set(files))  # Remove duplicates
                for filename in sorted(files):
                    self._load_command(filename, dir)

        msg = "Found {0} commands: {1}"
        commands = ", ".join(self._commands.keys())
        self.logger.info(msg.format(len(self._commands), commands))

    def get_all(self):
        """Return our dict of all loaded commands."""
        return self._commands

    def check(self, hook, data):
        """Given an IRC event, check if there's anything we can respond to."""
        with self._command_access_lock:
            for command in self._commands.values():
                if hook in command.hooks:
                    if command.check(data):
                        try:
                            command._wrap_process(data)
                        except Exception:
                            e = "Error executing command '{0}':"
                            self.logger.exception(e.format(data.command))
                        break
