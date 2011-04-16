# -*- coding: utf-8  -*-

## Imports
import re

from config.irc_config import *

from irc.connection import Connection
from irc.rc import RC

global frontend_conn

def get_connection():
    connection = Connection(WATCHER_HOST, WATCHER_PORT, NICK, IDENT, REALNAME)
    return connection

def main(connection, f_conn):
    global frontend_conn
    frontend_conn = f_conn
    connection.connect()
    read_buffer = str()

    while 1:
        try:        
            read_buffer = read_buffer + connection.get()
        except RuntimeError: # socket broke
            print "socket has broken on watcher, restarting component..."
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

def report(msg, chans):
    """send a message to a list of report channels on our front-end server"""
    for chan in chans:
        frontend_conn.say(chan, msg)

def check(rc):
    """check to see if """
    page_name = rc.page.lower()
    pretty_msg = rc.pretty()

    if "!earwigbot" in rc.msg.lower():
        report(pretty_msg, chans=BOT_CHANS)
    if re.match("wikipedia( talk)?:(wikiproject )?articles for creation", page_name):
        report(pretty_msg, chans=AFC_CHANS)
    elif re.match("wikipedia( talk)?:files for upload", page_name):
        report(pretty_msg, chans=AFC_CHANS)
    elif page_name.startswith("template:afc submission"):
        report(pretty_msg, chans=AFC_CHANS)
    if rc.flags == "delete" and re.match("deleted \"\[\[wikipedia( talk)?:(wikiproject )?articles for creation", rc.comment.lower()):
        report(pretty_msg, chans=AFC_CHANS)
