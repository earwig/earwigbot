# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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
In __init__, you can find some functions used to load and run these commands.
"""

import logging
import os
import sys

from earwigbot.classes import BaseCommand
from earwigbot.config import config

__all__ = ["load", "get_all", "check"]

# Base directory when searching for commands:
base_dir = os.path.dirname(os.path.abspath(__file__))

# Store commands in a dict, where the key is the command's name and the value
# is an instance of the command's class:
_commands = {}

# Logger for this module:
logger = logging.getLogger("earwigbot.tasks")

def _load_command(connection, filename):
    """Try to load a specific command from a module, identified by file name.

    Given a Connection object and a filename, we'll first try to import it,
    and if that works, make an instance of the 'Command' class inside (assuming
    it is an instance of BaseCommand), add it to _commands, and report the
    addition to the user. Any problems along the way will either be ignored or
    reported.
    """
    global _commands

    # Strip .py from the end of the filename and join with our package name:
    name = ".".join(("commands", filename[:-3]))
    try:
         __import__(name)
    except:
        logger.exception("Couldn't load file {0}".format(filename))
        return

    command = sys.modules[name].Command(connection)
    if not isinstance(command, BaseCommand):
        return

    _commands[command.name] = command
    logger.debug("Added command {0}".format(command.name))

def load(connection):
    """Load all valid commands into the _commands global variable.

    `connection` is a Connection object that is given to each command's
    constructor.
    """
    files = os.listdir(base_dir)
    files.sort()

    for filename in files:
        if filename.startswith("_") or not filename.endswith(".py"):
            continue
        try:
            _load_command(connection, filename)
        except AttributeError:
            pass  # The file is doesn't contain a command, so just move on

    msg = "Found {0} commands: {1}"
    logger.info(msg.format(len(_commands), ", ".join(_commands.keys())))

def get_all():
    """Return our dict of all loaded commands."""
    return _commands

def check(hook, data):
    """Given an event on IRC, check if there's anything we can respond to."""
    # Parse command arguments into data.command and data.args:
    data.parse_args()

    for command in _commands.values():
        if hook in command.hooks:
            if command.check(data):
                try:
                    command.process(data)
                except:
                    logger.exception("Error executing command '{0}'".format(data.command))
                break
