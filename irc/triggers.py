# -*- coding: utf-8  -*-

# Check what events on IRC we can respond to.

from irc.commands import test, help, git

def check(actions, data, hook):
    data.parse_args() # parse command arguments into data.command and data.args
    
    if hook == "join":
        pass

    if hook == "msg_private":
        pass

    if hook == "msg_public":
        pass

    if hook == "msg":
        if data.command == "!test":
            test.call(actions, data)
            
        elif data.command == "!help":
            help.call(actions, data)
            
        elif data.command == "!git":
            git.call(actions, data)
