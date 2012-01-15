# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import socket
import threading

__all__ = ["BrokenSocketException", "Connection"]

class BrokenSocketException(Exception):
    """A socket has broken, because it is not sending data. Raised by
    Connection.get()."""
    pass

class Connection(object):
    """A class to interface with IRC."""

    def __init__(self, host=None, port=None, nick=None, ident=None,
                 realname=None, logger=None):
        self.host = host
        self.port = port
        self.nick = nick
        self.ident = ident
        self.realname = realname
        self.logger = logger

        # A lock to prevent us from sending two messages at once:
        self.lock = threading.Lock()

    def connect(self):
        """Connect to our IRC server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
        except socket.error:
            self.logger.critical("Couldn't connect to IRC server", exc_info=1)
            exit(1)
        self.send("NICK %s" % self.nick)
        self.send("USER %s %s * :%s" % (self.ident, self.host, self.realname))

    def close(self):
        """Close our connection with the IRC server."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR) # shut down connection first
        except socket.error:
            pass # ignore if the socket is already down
        self.sock.close()

    def get(self, size=4096):
        """Receive (i.e. get) data from the server."""
        data = self.sock.recv(4096)
        if not data:
            # Socket isn't giving us any data, so it is dead or broken:
            raise BrokenSocketException()
        return data

    def send(self, msg):
        """Send data to the server."""
        # Ensure that we only send one message at a time with a blocking lock:
        with self.lock:
            self.sock.sendall(msg + "\r\n")
            self.logger.debug(msg)

    def say(self, target, msg):
        """Send a private message to a target on the server."""
        message = "".join(("PRIVMSG ", target, " :", msg))
        self.send(message)

    def reply(self, data, msg):
        """Send a private message as a reply to a user on the server."""
        message = "".join((chr(2), data.nick, chr(0x0f), ": ", msg))
        self.say(data.chan, message)

    def action(self, target, msg):
        """Send a private message to a target on the server as an action."""
        message = "".join((chr(1), "ACTION ", msg, chr(1)))
        self.say(target, message)

    def notice(self, target, msg):
        """Send a notice to a target on the server."""
        message = "".join(("NOTICE ", target, " :", msg))
        self.send(message)

    def join(self, chan):
        """Join a channel on the server."""
        message = " ".join(("JOIN", chan))
        self.send(message)

    def part(self, chan):
        """Part from a channel on the server."""
        message = " ".join(("PART", chan))
        self.send(message)

    def mode(self, chan, level, msg):
        """Send a mode message to the server."""
        message = " ".join(("MODE", chan, level, msg))
        self.send(message)
