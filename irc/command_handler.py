# -*- coding: utf-8  -*-

# A module to manage IRC commands.

import os
import traceback

commands = []

def init_commands(connection):
    """load all valid command classes from irc/commmands/ into the commands variable"""
    files = os.listdir(os.path.join("irc", "commands")) # get all files in irc/commands/

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

        m = eval(module) # 'module' is a string, so get the actual object for processing
        process_module(connection, m)

    pretty_cmnds = map(lambda c: c.__class__.__name__, commands)
    print "Found %s command classes: %s." % (len(commands), ', '.join(pretty_cmnds))

def process_module(connection, module):
    """go through all objects in a module and add valid command classes to the commands variable"""
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
                commands.append(command)
                print "Added command class %s from %s..." % (this_obj, module.__name__)
                continue

def get_commands():
    """get our commands"""
    return commands

def check(hook, data):
    """given an event on IRC, check if there's anything we can respond to by calling each command class"""
    data.parse_args() # parse command arguments into data.command and data.args

    for command in commands:
        if command.get_hook() == hook:
            if command.check(data):
                command.process(data)
                break
