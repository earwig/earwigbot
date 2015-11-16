# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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
from time import sleep, time

from earwigbot.exceptions import BrokenSocketError

__all__ = ["IRCConnection"]

class IRCConnection(object):
    """Interface with an IRC server."""

    def __init__(self, host, port, nick, ident, realname, logger):
        self._host = host
        self._port = port
        self._nick = nick
        self._ident = ident
        self._realname = realname
        self.logger = logger

        self._is_running = False
        self._send_lock = Lock()

        self._last_recv = time()
        self._last_send = 0
        self._last_ping = 0
        self._myhost = "." * 63  # default: longest possible hostname

    def __repr__(self):
        """Return the canonical string representation of the IRCConnection."""
        res = "IRCConnection(host={0!r}, port={1!r}, nick={2!r}, ident={3!r}, realname={4!r})"
        return res.format(self.host, self.port, self.nick, self.ident,
                          self.realname)

    def __str__(self):
        """Return a nice string representation of the IRCConnection."""
        res = "<IRCConnection {0}!{1} at {2}:{3}>"
        return res.format(self.nick, self.ident, self.host, self.port)

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
        """Completely close our connection with the IRC server."""
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

    def _send(self, msg, hidelog=False):
        """Send data to the server."""
        with self._send_lock:
            time_since_last = time() - self._last_send
            if time_since_last < 0.75:
                sleep(0.75 - time_since_last)
            try:
                self._sock.sendall(msg + "\r\n")
            except socket.error:
                self._is_running = False
            else:
                if not hidelog:
                    self.logger.debug(msg)
                self._last_send = time()

    def _get_maxlen(self, extra):
        """Return our best guess of the maximum length of a standard message.

        This applies mainly to PRIVMSGs and NOTICEs.
        """
        base_max = 512
        userhost = len(self.nick) + len(self.ident) + len(self._myhost) + 2
        padding = 4  # "\r\n" at end, ":" at beginning, and " " after userhost
        return base_max - userhost - padding - extra

    def _split(self, msgs, extralen, maxsplits=3):
        """Split a large message into multiple messages."""
        maxlen = self._get_maxlen(extralen)
        words = msgs.split(" ")
        splits = 0
        while words and splits < maxsplits:
            splits += 1
            if len(words[0]) > maxlen:
                word = words.pop(0)
                yield word[:maxlen]
                words.insert(0, word[maxlen:])
            else:
                msg = []
                while words and len(" ".join(msg + [words[0]])) <= maxlen:
                    msg.append(words.pop(0))
                yield " ".join(msg)

    def _quit(self, msg=None):
        """Issue a quit message to the server. Doesn't close the connection."""
        if msg:
            self._send("QUIT :{0}".format(msg))
        else:
            self._send("QUIT")

    def _process_defaults(self, line):
        """Default process hooks for lines received on IRC."""
        self._last_recv = time()
        if line[0] == "PING":  # If we are pinged, pong back
            self.pong(line[1][1:])
        elif line[1] == "001":  # Update nickname on startup
            if line[2] != self.nick:
                self.logger.warn("Nickname changed from {0} to {1}".format(
                    self.nick, line[2]))
                self._nick = line[2]
        elif line[1] == "376":  # After sign-on, get our userhost
            self._send("WHOIS {0}".format(self.nick))
        elif line[1] == "311":  # Receiving WHOIS result
            if line[2] == self.nick:
                self._ident = line[4]
                self._myhost = line[5]
        elif line[1] == "396":  # Hostname change
            self._myhost = line[3]

    def _process_message(self, line):
        """To be overridden in subclasses."""
        raise NotImplementedError()

    @property
    def host(self):
        """The hostname of the IRC server, like ``"irc.freenode.net"``."""
        return self._host

    @property
    def port(self):
        """The port of the IRC server, like ``6667``."""
        return self._port

    @property
    def nick(self):
        """Our nickname on the server, like ``"EarwigBot"``."""
        return self._nick

    @property
    def ident(self):
        """Our ident on the server, like ``"earwig"``.

        See http://en.wikipedia.org/wiki/Ident.
        """
        return self._ident

    @property
    def realname(self):
        """Our realname (gecos field) on the server."""
        return self._realname

    def say(self, target, msg, hidelog=False):
        """Send a private message to a target on the server."""
        for msg in self._split(msg, len(target) + 10):
            msg = "PRIVMSG {0} :{1}".format(target, msg)
            self._send(msg, hidelog)

    def reply(self, data, msg, hidelog=False):
        """Send a private message as a reply to a user on the server."""
        if data.is_private:
            self.say(data.chan, msg, hidelog)
        else:
            msg = "\x02{0}\x0F: {1}".format(data.reply_nick, msg)
            self.say(data.chan, msg, hidelog)

    def action(self, target, msg, hidelog=False):
        """Send a private message to a target on the server as an action."""
        msg = "\x01ACTION {0}\x01".format(msg)
        self.say(target, msg, hidelog)

    def notice(self, target, msg, hidelog=False):
        """Send a notice to a target on the server."""
        for msg in self._split(msg, len(target) + 9):
            msg = "NOTICE {0} :{1}".format(target, msg)
            self._send(msg, hidelog)

    def join(self, chan, hidelog=False):
        """Join a channel on the server."""
        msg = "JOIN {0}".format(chan)
        self._send(msg, hidelog)

    def part(self, chan, msg=None, hidelog=False):
        """Part from a channel on the server, optionally using an message."""
        if msg:
            self._send("PART {0} :{1}".format(chan, msg), hidelog)
        else:
            self._send("PART {0}".format(chan), hidelog)

    def mode(self, target, level, msg, hidelog=False):
        """Send a mode message to the server."""
        msg = "MODE {0} {1} {2}".format(target, level, msg)
        self._send(msg, hidelog)

    def ping(self, target, hidelog=False):
        """Ping another entity on the server."""
        msg = "PING {0}".format(target)
        self._send(msg, hidelog)

    def pong(self, target, hidelog=False):
        """Pong another entity on the server."""
        msg = "PONG {0}".format(target)
        self._send(msg, hidelog)

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
                line = line.strip().split()
                self._process_defaults(line)
                self._process_message(line)
            if self.is_stopped():
                break

        self._close()

    def keep_alive(self):
        """Ensure that we stay connected, stopping if the connection breaks."""
        now = time()
        if now - self._last_recv > 120:
            if self._last_ping < self._last_recv:
                log = "Last message was received over 120 seconds ago. Pinging."
                self.logger.debug(log)
                self.ping(self.host)
                self._last_ping = now
            elif now - self._last_ping > 60:
                self.logger.debug("No ping response in 60 seconds. Stopping.")
                self.stop()

    def stop(self, msg=None):
        """Request the IRC connection to close at earliest convenience."""
        if self._is_running:
            self._quit(msg)
            self._is_running = False

    def is_stopped(self):
        """Return whether the IRC connection has been (or is to be) closed."""
        return not self._is_running
