# -*- coding: utf-8  -*-

# Actions/commands to interface with IRC.

import string

class Actions:
    def __init__(self, sock):
        """actions/commands to interface with IRC"""
        self.sock = sock

    def get(self, size = 4096):
        """receive (get) data from the server"""
        data = self.sock.recv(4096)
        if not data:
            raise RuntimeError("socket is dead")
        return data

    def send(self, msg):
        """send data to the server"""
        self.sock.send(msg + "\r\n")
        print "   %s" % msg

    def say(self, target, msg):
        """send a message"""
        self.send("PRIVMSG %s :%s" % (target, msg))

    def action(self, target, msg):
        """send a message as an action"""
        self.say(target,"%sACTION %s%s" % (chr(1), msg, chr(1)))

    def notice(self, target, msg): 
        """send a notice"""
        self.send("NOTICE %s :%s" % (target, msg))

    def join(self, chan):
        """join a channel"""
        self.send("JOIN %s" % chan)
