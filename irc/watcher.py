# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Watcher Component

The IRC watcher runs on a wiki recent-changes server and listens for edits.
Users cannot interact with this part of the bot. When an event occurs, run it
through irc/watcher_logic.py's process() function, which can result in either
wiki bot tasks being started (listed in wiki/tasks/) or messages being sent to
channels in the IRC frontend.
"""

from core import config
from irc.connection import *
from irc.rc import RC
from irc import watcher_logic

frontend_conn = None

def get_connection():
    """Return a new Connection() instance with information about our server
    connection, but don't actually connect yet."""
    cf = config.irc.watcher
    connection = Connection(cf.host, cf.port, cf.nick, cf.nick, cf.realname)
    return connection

def main(connection, f_conn=None):
    """Main loop for the Watcher IRC Bot component. get_connection() should
    have already been called and the connection should have been started with
    connection.connect(). Accept the frontend connection as well as an optional
    parameter in order to send messages directly to frontend IRC channels."""
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

                # ignore messages originating from channels not in our list, to
                # prevent someone PMing us false data
                if chan not in config.irc.watcher.channels:
                    continue

                msg = ' '.join(line[3:])[1:]
                rc = RC(msg)  # new RC object to store this event's data
                rc.parse()  # parse a message into pagenames, usernames, etc.
                process(rc)  # report to frontend channels or start tasks

            if line[0] == "PING":  # if we are pinged, pong back to the server
                connection.send("PONG %s" % line[1])

            # when we've finished starting up, join all watcher channels
            if line[1] == "376":
                for chan in config.irc.watcher.channels:
                    connection.join(chan)

def process(rc):
    """Process a message from IRC (technically, an RC object). The actual
    processing is configurable, so we don't have that hard-coded here. We
    simply call irc/watcher_logic.py's process() function and expect a list of
    channels back, which we report the event data to."""
    chans = watcher_logic.process(rc)
    if chans and frontend_conn:
        pretty = rc.get_pretty()
        for chan in chans:
            frontend_conn.say(chan, pretty)
