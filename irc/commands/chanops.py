# -*- coding: utf-8  -*-

"""Voice/devoice/op/deop users in the channel."""

from config.irc_config import *

connection, data = None, None

def call(c, d):
    global connection, data
    connection, data = c, d

    if data.host not in ADMINS:
        connection.reply(data.chan, data.nick, "you must be a bot admin to use this command.")
        return

    if not data.args: # if it is just !op/!devoice/whatever without arguments, assume they want to do this to themselves
        target = data.nick
    else:
        target = data.args[0]

    action = data.command[1:] # strip ! at the beginning of the command

    connection.say("ChanServ", "%s %s %s" % (action, data.chan, target))
