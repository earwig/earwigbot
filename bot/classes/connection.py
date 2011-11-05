# -*- coding: utf-8  -*-

import socket
import threading

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
        self.sock.connect((self.host, self.port))
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
