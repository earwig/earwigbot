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
from threading import Lock
from time import sleep

from earwigbot.exceptions import BrokenSocketError

__all__ = ["IRCConnection"]

class IRCConnection(object):
    """Interface with an IRC server."""

    def __init__(self, host, port, nick, ident, realname):
        self.host = host
        self.port = port
        self.nick = nick
        self.ident = ident
        self.realname = realname
        self._is_running = False

        # A lock to prevent us from sending two messages at once:
        self._send_lock = Lock()

    def _connect(self):
        """Connect to our IRC server."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sock.connect((self.host, self.port))
        except socket.error:
            self.logger.exception("Couldn't connect to IRC server; retrying")
            sleep(8)
            self._connect()
        self._send("NICK {0}".format(self.nick))
        self._send("USER {0} {1} * :{2}".format(self.ident, self.host, self.realname))

    def _close(self):
        """Close our connection with the IRC server."""
        try:
            self._sock.shutdown(socket.SHUT_RDWR)  # Shut down connection first
        except socket.error:
            pass  # Ignore if the socket is already down
        self._sock.close()

    def _get(self, size=4096):
        """Receive (i.e. get) data from the server."""
        data = self._sock.recv(size)
        if not data:
            # Socket isn't giving us any data, so it is dead or broken:
            raise BrokenSocketError()
        return data

    def _send(self, msg):
        """Send data to the server."""
        with self._send_lock:
            self._sock.sendall(msg + "\r\n")
            self.logger.debug(msg)

    def _quit(self, msg=None):
        """Issue a quit message to the server."""
        if msg:
            self._send("QUIT :{0}".format(msg))
        else:
            self._send("QUIT")

    def say(self, target, msg):
        """Send a private message to a target on the server."""
        msg = "PRIVMSG {0} :{1}".format(target, msg)
        self._send(msg)

    def reply(self, data, msg):
        """Send a private message as a reply to a user on the server."""
        msg = "\x02{0}\x0f: {1}".format(data.nick, msg)
        self.say(data.chan, msg)

    def action(self, target, msg):
        """Send a private message to a target on the server as an action."""
        msg = "\x01ACTION {0}\x01".format(msg)
        self.say(target, msg)

    def notice(self, target, msg):
        """Send a notice to a target on the server."""
        msg = "NOTICE {0} :{1}".format(target, msg)
        self._send(msg)

    def join(self, chan):
        """Join a channel on the server."""
        msg = "JOIN {0}".format(chan)
        self._send(msg)

    def part(self, chan, msg=None):
        """Part from a channel on the server, optionally using an message."""
        if msg:
            self._send("PART {0} :{1}".format(chan, msg))
        else:
            self._send("PART {0}".format(chan))

    def mode(self, target, level, msg):
        """Send a mode message to the server."""
        msg = "MODE {0} {1} {2}".format(target, level, msg)
        self._send(msg)

    def pong(self, target):
        """Pong another entity on the server."""
        msg = "PONG {0}".format(target)
        self._send(msg)

    def loop(self):
        """Main loop for the IRC connection."""
        self._is_running = True
        read_buffer = ""
        while 1:
            try:
                read_buffer += self._get()
            except BrokenSocketError:
                self._is_running = False
                break

            lines = read_buffer.split("\n")
            read_buffer = lines.pop()
            for line in lines:
                self._process_message(line)
            if self.is_stopped():
                self._close()
                break

    def stop(self, msg=None):
        """Request the IRC connection to close at earliest convenience."""
        if self._is_running:
            self._quit(msg)
            self._is_running = False

    def is_stopped(self):
        """Return whether the IRC connection has been (or is to be) closed."""
        return not self._is_running
