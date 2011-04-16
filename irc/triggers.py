# -*- coding: utf-8  -*-

# Check what events on IRC we can respond to.

from irc.commands import test, help, git, link

def check(connection, data, hook):
    data.parse_args() # parse command arguments into data.command and data.args
    
    if hook == "join":
        pass

    if hook == "msg_private":
        pass

    if hook == "msg_public":
        pass

    if hook == "msg":
        if data.command == "!test":
            test.call(connection, data)
            
        elif data.command == "!help":
            help.call(connection, data)
            
        elif data.command == "!git":
            git.call(connection, data)

        elif (data.command == "!link" or
        ("[[" in data.msg and "]]" in data.msg) or
        ("{{" in data.msg and "}}" in data.msg)):
            link.call(connection, data)
