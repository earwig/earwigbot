# -*- coding: utf-8  -*-

## Imports
import socket, re, time

from config.irc_config import *
from config.secure_config import *

from irc import triggers
from irc.actions import *
from irc.data import *

def main():
    read_buffer = str()

    while 1:
        try:        
            read_buffer = read_buffer + actions.get()
        except RuntimeError: # socket broke
            print "socket has broken, sleeping for a minute and restarting..."
            time.sleep(60) # sleep for sixty seconds
            return # then exit our loop and restart the bot

        lines = read_buffer.split("\n")
        read_buffer = lines.pop()

        for line in lines:
            line = line.strip().split("\n")
            data = Data()

            if line[1] == "JOIN":
                data.nick, data.ident, data.host = re.findall(":(.*?)!(.*?)@(.*?)\Z", line[0])[0]
                data.chan = line[2][1:]

                triggers.check(actions, data, "join") # check if there's anything we can respond to, and if so, respond

            if line[1] == "PRIVMSG":
                data.nick, data.ident, data.host = re.findall(":(.*?)!(.*?)@(.*?)\Z", line[0])[0]
                data.msg = ' '.join(line[3:])[1:]
                data.chan = line[2]

                if data.chan == NICK: # this is a privmsg to us, so set 'chan' as the nick of the sender
                    data.chan = data.nick
                    triggers.check(actions, data, "msg_private") # only respond if it's a private message
                else:
                    triggers.check(actions, data, "msg_public") # only respond if it's a public (channel) message

                triggers.check(actions, data, "msg") # check for general messages

                if data.msg == "!restart": # hardcode the !restart command (we can't return from within actions.py)
                    if data.host in ADMINS:
                        return True                        

            if line[0] == "PING": # If we are pinged, pong back to the server
                actions.send("PONG %s" % line[1])

            if line[1] == "376":
                if NS_AUTH: # if we're supposed to auth to nickserv, do that
                    actions.say("NickServ", "IDENTIFY %s %s" % (NS_USER, NS_PASS))
                for chan in CHANS: # join all of our startup channels
                    actions.join(chan)

if __name__ == "__main__":
    sock = socket.socket()
    sock.connect((HOST, PORT))
    actions = Actions(sock)
    actions.send("NICK %s" % NICK)
    actions.send("USER %s %s bla :%s" % (IDENT, HOST, REALNAME))
    main()
