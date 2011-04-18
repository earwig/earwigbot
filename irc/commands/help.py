# -*- coding: utf-8  -*-

"""Generates help information."""

connection, data = None, None

def get_alias(key):
    """connect command aliases with their file, e.g. so we know !voice corresponds to chanops.py"""
    aliases = {
        "voice": "chanops",
        "devoice": "chanops",
        "op": "chanops",
        "deop": "chanops",
    }
    return aliases[key]

def call(c, d):
    global connection, data
    connection, data = c, d

    if not data.args:
        do_general_help()

    else:
        do_command_help()

def do_general_help():
    connection.reply(data.chan, data.nick, "I am a bot! You can get help for any command by typing '!help <command>'.")

def do_command_help():
    command = data.args[0]

    try:
        exec "from irc.commands import %s as this_command" % command
    except ImportError: # if we can't find it directly, this could be an alias for another command
        try:
            cmd = get_alias(command)
        except KeyError:
            connection.reply(data.chan, data.nick, "command \x0303%s\x0301 not found!" % command)
            return
        exec "from irc.commands import %s as this_command" % cmd

    info = this_command.__doc__

    if info:
        connection.reply(data.chan, data.nick, "info for command \x0303%s\x0301: \"%s\"" % (command, info))
    else:
        connection.reply(data.chan, data.nick, "sorry, no information for \x0303%s\x0301." % command)
