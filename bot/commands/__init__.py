# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Command Manager

This package provides the IRC "commands" used by the bot's front-end component.
In __init__, you can find some functions used to load and run these commands.
"""

import os
import sys
import traceback

from classes import BaseCommand
import config

__all__ = ["load", "get_all", "check"]

# Base directory when searching for commands:
base_dir = os.path.join(config.root_dir, "bot", "commands")

# Store commands in a dict, where the key is the command's name and the value
# is an instance of the command's class:
_commands = {}

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
        print "Couldn't load file {0}:".format(filename)
        traceback.print_exc()
        return

    command = sys.modules[name].Command(connection)
    if not isinstance(command, BaseCommand):
        return

    _commands[command.name] = command
    print "Added command {0}...".format(command.name)

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

    msg = "Found {0} commands: {1}."
    print msg.format(len(_commands), ", ".join(_commands.keys()))

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
                    print "Error executing command '{0}':".format(data.command)
                    traceback.print_exc()
                break
