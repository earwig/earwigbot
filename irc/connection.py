# -*- coding: utf-8  -*-

# A class to interface with IRC.

import socket
import threading

class BrokenSocketException(Exception):
    """A socket has broken, because it is not sending data."""
    pass

class Connection(object):
    def __init__(self, host=None, port=None, nick=None, ident=None, realname=None):
        """a class to interface with IRC"""
        self.host = host
        self.port = port
        self.nick = nick
        self.ident = ident
        self.realname = realname

    def connect(self):
        """connect to IRC"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.send("NICK %s" % self.nick)
        self.send("USER %s %s * :%s" % (self.ident, self.host, self.realname))

    def close(self):
        """close our connection with IRC"""
        try:
            self.sock.shutdown(socket.SHUT_RDWR) # shut down connection first
        except socket.error:
            pass # ignore if the socket is already down
        self.sock.close()

    def get(self, size=4096):
        """receive (get) data from the server"""
        data = self.sock.recv(4096)
        if not data: # socket giving us no data, so it is dead/broken
            raise BrokenSocketException()
        return data

    def send(self, msg):
        """send data to the server"""
        lock = threading.Lock()
        lock.acquire() # ensure that we only send one message at a time (blocking)
        try:
            self.sock.sendall(msg + "\r\n")
            print "   %s" % msg
        finally:
            lock.release()

    def say(self, target, msg):
        """send a message"""
        self.send("PRIVMSG %s :%s" % (target, msg))

    def reply(self, data, msg):
        """send a message as a reply"""
        self.say(data.chan, "%s%s%s: %s" % (chr(2), data.nick, chr(0x0f), msg))

    def action(self, target, msg):
        """send a message as an action"""
        self.say(target,"%sACTION %s%s" % (chr(1), msg, chr(1)))

    def notice(self, target, msg): 
        """send a notice"""
        self.send("NOTICE %s :%s" % (target, msg))

    def join(self, chan):
        """join a channel"""
        self.send("JOIN %s" % chan)
