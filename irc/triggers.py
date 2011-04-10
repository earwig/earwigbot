# -*- coding: utf-8  -*-

# Check what events on IRC we can respond to.

from irc.commands import test, git

def check(actions, data, hook):
    if hook == "join":
        pass

    if hook == "msg_private":
        pass

    if hook == "msg_public":
        pass

    if hook == "msg":
        if data.msg == "!test":
            test.call(actions, data)
        if data.msg.startswith("!git"):
            git.call(actions, data)
