# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Frontend Component

The IRC frontend runs on a normal IRC server and expects users to interact with
it and give it commands. Commands are stored as "command classes", subclasses
of BaseCommand in irc/base_command.py. All command classes are automatically
imported by irc/command_handler.py if they are in irc/commands.
"""

import re

import config
import commands
from classes import Connection, Data, BrokenSocketException

__all__ = ["get_connection", "startup", "main"]

connection = None
sender_regex = re.compile(":(.*?)!(.*?)@(.*?)\Z")

def get_connection():
    """Return a new Connection() instance with information about our server
    connection, but don't actually connect yet."""
    cf = config.irc["frontend"]
    connection = Connection(cf["host"], cf["port"], cf["nick"], cf["ident"],
            cf["realname"])
    return connection

def startup(conn):
    """Accept a single arg, a Connection() object, and set our global variable
    'connection' to it. Load all command classes in irc/commands with
    command_handler, and then establish a connection with the IRC server."""
    global connection
    connection = conn
    commands.load(connection)
    connection.connect()

def main():
    """Main loop for the frontend component.

    get_connection() and startup() should have already been called before this.
    """
    read_buffer = str()

    while 1:
        try:
            read_buffer = read_buffer + connection.get()
        except BrokenSocketException:
            print "Socket has broken on front-end; restarting bot..."
            return

        lines = read_buffer.split("\n")
        read_buffer = lines.pop()
        for line in lines:
            ret = _process_message(line)
            if ret:
                return

def _process_message(line):
    """Process a single message from IRC."""
    line = line.strip().split()
    data = Data(line)  # new Data instance to store info about this line

    if line[1] == "JOIN":
        data.nick, data.ident, data.host = sender_regex.findall(line[0])[0]
        data.chan = line[2]
        # Check for 'join' hooks in our commands:
        commands.check("join", data)

    elif line[1] == "PRIVMSG":
        data.nick, data.ident, data.host = sender_regex.findall(line[0])[0]
        data.msg = ' '.join(line[3:])[1:]
        data.chan = line[2]

        if data.chan == config.irc["frontend"]["nick"]:
            # This is a privmsg to us, so set 'chan' as the nick of the, sender
            # then check for private-only command hooks:
            data.chan = data.nick
            commands.check("msg_private", data)
        else:
            # Check for public-only command hooks:
            commands.check("msg_public", data)

        # Check for command hooks that apply to all messages:
        commands.check("msg", data)

        # Hardcode the !restart command (we can't restart from within an
        # ordinary command):
        if data.msg in ["!restart", ".restart"]:
            if data.host in config.irc["permissions"]["owners"]:
                print "Restarting bot per owner request..."
                return True

    # If we are pinged, pong back:
    elif line[0] == "PING":
        msg = " ".join(("PONG", line[1]))
        connection.send(msg)

    # On successful connection to the server:
    elif line[1] == "376":
        # If we're supposed to auth to NickServ, do that:
        try:
            username = config.irc["frontend"]["nickservUsername"]
            password = config.irc["frontend"]["nickservPassword"]
        except KeyError:
            pass
        else:
            msg = " ".join(("IDENTIFY", username, password))
            connection.say("NickServ", msg)

        # Join all of our startup channels:
        for chan in config.irc["frontend"]["channels"]:
            connection.join(chan)
