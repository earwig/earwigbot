# -*- coding: utf-8  -*-

## Imports
from config.irc import *
from config.main import *
from config.watcher import *

from irc.connection import *
from irc.rc import RC

global frontend_conn

def get_connection():
    connection = Connection(WATCHER_HOST, WATCHER_PORT, NICK, IDENT, REALNAME)
    return connection

def main(connection, f_conn):
    global frontend_conn
    frontend_conn = f_conn
    read_buffer = str()

    while 1:
        try:
            read_buffer = read_buffer + connection.get()
        except BrokenSocketException:
            return

        lines = read_buffer.split("\n")
        read_buffer = lines.pop()

        for line in lines:
            line = line.strip().split()

            if line[1] == "PRIVMSG":
                chan = line[2]
                if chan != WATCHER_CHAN: # if we're getting a msg from another channel, ignore it
                    continue

                msg = ' '.join(line[3:])[1:]
                rc = RC(msg) # create a new RC object to store this change's data
                rc.parse()
                check(rc)

            if line[0] == "PING": # If we are pinged, pong back to the server
                connection.send("PONG %s" % line[1])

            if line[1] == "376": # Join the recent changes channel when we've finished starting up
                connection.join(WATCHER_CHAN)

def check(rc):
    """check if we're supposed to report this message anywhere"""
    results = process(rc) # process the message in config/watcher.py, and get a list of channels to send it to
    if not results:
        return
    pretty = rc.get_pretty()
    if enable_irc_frontend:
        for chan in results:
            frontend_conn.say(chan, pretty)
