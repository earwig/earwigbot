# -*- coding: utf-8  -*-

"""Generates help information."""

actions, data = None, None

def call(a, d):
    global actions, data
    actions, data = a, d

    if not data.args:
        do_general_help()

    else:
        do_command_help()

def do_general_help():
    actions.say(data.chan, "\x02%s\x0F: I am a bot! You can get help for any command by typing '!help <command>'." % (data.nick))

def do_command_help():
    command = data.args[0]

    try:
        exec "from irc.commands import %s as this_command" % command
    except ImportError:
        actions.say(data.chan, "\x02%s\x0F: command \x0303%s\x0301 not found!" % (data.nick, command))
        return

    info = this_command.__doc__

    if info:
        actions.say(data.chan, "\x02%s\x0F: Info for command \"\x0303%s\x0301: %s\"" % (data.nick, command, info))
    else:
        actions.say(data.chan, "\x02%s\x0F: Sorry, no information for \x0303%s\x0301." % (data.nick, command))
