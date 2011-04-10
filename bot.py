# -*- coding: utf-8  -*-

## Imports
import socket, string, re
from actions import *
from config.irc_config import *
from config.secure_config import *

def send(msg): # send a message 'msg' to the server
    s.send(msg + "\r\n")
    print "   %s" % msg

def say(target, msg): # send a private message 'msg' to 'target'
    send("PRIVMSG %s :%s" % (target, msg))

def action(target, msg): # send a message as an action
    say(target,"%sACTION %s%s" % (chr(1), msg, chr(1)))

def notice(target, msg): # send a notice 'msg' to 'target'
    send("NOTICE %s :%s" % (target, msg))

def join(chan): # join channel 'chan'
    send("JOIN %s" % chan)

cmds = (s, send, say, action, notice, join) # pack up commands

def main():
    readbuffer = str()
    data = [s, send, say, notice, join]
    while 1:
        readbuffer = readbuffer + s.recv(1024)
        temp = string.split(readbuffer, "\n")
        readbuffer = temp.pop()
        for line in temp:
            line2 = string.split(string.rstrip(line))

            if line2[1] == "JOIN":
                nick, ident, host = re.findall(":(.*?)!(.*?)@(.*?)\Z", line2[0])[0]
                chan = line2[2][1:]

                check_triggers(cmds, "join", nick, ident, host, chan) # check if there's anything we can respond to, and if so, respond

            if line2[1] == "PRIVMSG":
                nick, ident, host = re.findall(":(.*?)!(.*?)@(.*?)\Z", line2[0])[0]
                msg = ' '.join(line2[3:])[1:]
                chan = line2[2]

                if chan == NICK: # if line2[2] is us, this is a privmsg to us, so set 'chan' as the nick of the sender
                    chan = nick
                    check_triggers(cmds, "msg_private", nick, ident, host, chan, msg) # only respond if it's a private message
                else:
                    check_triggers(cmds, "msg_public", nick, ident, host, chan, msg) # only respond if it's a public (channel) message

                check_triggers(cmds, "msg", nick, ident, host, chan, msg) # check for general messages

                if msg == "!restart": # hardcode the !restart command (we can't return from within actions.py)
                    if host in ADMINS:
                        return True                        

            if line2[0] == "PING": # If we are pinged, pong back to the server
                send("PONG %s" % line2[1])

            if line2[1] == "376":
                if NS_AUTH:
                    say("NickServ", "IDENTIFY %s %s" % (NS_USER, NS_PASS))
                for this_chan in CHANS: # join all of our startup channels
                    join(this_chan)

if __name__ == "__main__":
    s = socket.socket()
    s.connect((HOST, PORT))
    send("NICK %s" % NICK)
    send("USER %s %s bla :%s" % (IDENT, HOST, REALNAME))
    main()
