# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Front-end Component

The IRC frontend runs on a normal IRC server and expects users to interact with
it and give it commands. Commands are stored as "command classes", subclasses
of BaseCommand in irc/base_command.py. All command classes are automatically
imported by irc/command_handler.py if they are in irc/commands.
"""

from re import findall

from core import config
from irc import command_handler
from irc.classes import Connection, Data, BrokenSocketException

connection = None

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
    command_handler.load_commands(connection)
    connection.connect()

def main():
    """Main loop for the Frontend IRC Bot component. get_connection() and
    startup() should have already been called."""
    read_buffer = str()

    while 1:
        try:        
            read_buffer = read_buffer + connection.get()
        except BrokenSocketException:
            print "Socket has broken on front-end; restarting bot..."
            return

        lines = read_buffer.split("\n")
        read_buffer = lines.pop()

        for line in lines:  # handle a single message from IRC
            line = line.strip().split()
            data = Data()  # new Data() instance to store info about this line
            data.line = line

            if line[1] == "JOIN":
                data.nick, data.ident, data.host = findall(
                        ":(.*?)!(.*?)@(.*?)\Z", line[0])[0]
                data.chan = line[2][1:]
                command_handler.check("join", data) # check for 'join' hooks in
                                                    # our commands

            if line[1] == "PRIVMSG":
                data.nick, data.ident, data.host = findall(
                        ":(.*?)!(.*?)@(.*?)\Z", line[0])[0]
                data.msg = ' '.join(line[3:])[1:]
                data.chan = line[2]

                if data.chan == config.irc["frontend"]["nick"]:
                    # this is a privmsg to us, so set 'chan' as the nick of the
                    # sender, then check for private-only command hooks
                    data.chan = data.nick
                    command_handler.check("msg_private", data)
                else:
                    # check for public-only command hooks
                    command_handler.check("msg_public", data)

                # check for command hooks that apply to all messages
                command_handler.check("msg", data)

                # hardcode the !restart command (we can't restart from within
                # an ordinary command)
                if data.msg in ["!restart", ".restart"]:
                    if data.host in config.irc["permissions"]["owners"]:
                        print "Restarting bot per owner request..."
                        return

            if line[0] == "PING":  # if we are pinged, pong back to the server
                connection.send("PONG %s" % line[1])

            if line[1] == "376":  # we've successfully connected to the network
                try:  # if we're supposed to auth to nickserv, do that
                    ns_username = config.irc["frontend"]["nickservUsername"]
                    ns_password = config.irc["frontend"]["nickservPassword"]
                except KeyError:
                    pass
                else:
                    connection.say("NickServ", "IDENTIFY {0} {1}".format(
                            ns_username, ns_password))
                
                # join all of our startup channels
                for chan in config.irc["frontend"]["channels"]:
                    connection.join(chan)
