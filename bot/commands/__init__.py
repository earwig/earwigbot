# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Command Manager

This package provides the IRC "commands" used by the bot's front-end component.
In __init__, you can find some functions used to load and run these commands.
"""

import os
import traceback

__all__ = ["load", "get_all", "check"]

# Store commands in a dict, where the key is the command's name and the value
# is an instance of the command's class:
_commands = {}

def _load_class_from_file(connection, module):
    """Add."""
    global commands
    objects = dir(module)

    for this_obj in objects: # go through everything in the file
        obj = eval("module.%s" % this_obj) # this_obj is a string, so get the actual object corresponding to that string

        try:
            bases = obj.__bases__
        except AttributeError: # object isn't a valid class, so ignore it
            continue

        for base in bases:
            if base.__name__ == "BaseCommand": # this inherits BaseCommand, so it must be a command class
                command = obj(connection) # initialize a new command object
                _commands.append(command)
                print "Added command class %s from %s..." % (this_obj, module.__name__)
                continue

def load(connection):
    """Load all valid commands into the _commands global variable."""
    files = os.listdir(os.path.join("bot", "commands"))
    files.sort()

    for f in files:
        if f.startswith("_") or not f.endswith(".py"): # ignore non-python files or files beginning with "_"
            continue
        module = f[:-3] # strip .py from end
        try:
            exec "from irc.commands import %s" % module
        except: # importing the file failed for some reason...
            print "Couldn't load file %s:" % f
            traceback.print_exc()
            continue
        process_module(connection, eval(module)) # 'module' is a string, so get the actual object for processing by eval-ing it

    pretty_cmnds = map(lambda c: c.__class__.__name__, commands)
    print "Found %s command classes: %s." % (len(commands), ', '.join(pretty_cmnds))

def get_all():
    """Return our dict of all loaded commands."""
    return _commands

def check(hook, data):
    """Given an event on IRC, check if there's anything we can respond to."""
    # parse command arguments into data.command and data.args
    data.parse_args()

    for command in _commands:
        if hook in command.get_hooks():
            if command.check(data):
                try:
                    command.process(data)
                except:
                    print "Error executing command '{}':".format(data.command)
                    traceback.print_exc() # catch exceptions and print them
                break
