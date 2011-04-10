# -*- coding: utf-8  -*-

import string, re, subprocess
from config import *

s, send, say, action, notice, join = None, None, None, None, None, None

def check_triggers(cmds, act, nick, ident, host, chan, msg = None):
    global s, send, say, action, notice, join # set commands as globals so we can use them in other functions
    s, send, say, action, notice, join = cmds # unpack commands

    if act == "join":
        pass

    if act == "msg_private":
        pass

    if act == "msg_public":
        pass

    if act == "msg":
        if msg == "!test":
            cmd_test(nick, chan)
        if msg.startswith("!git"):
            cmd_git(nick, host, chan, msg)

def get_args(msg): # get command arguments
    args = msg.strip().split(' ') # strip out extra whitespace and split the message into a list
    while '' in args: # remove any empty arguments
        args.remove('')
    return args[1:] # remove the command itself

def cmd_test(nick, chan): # bot test
    say(chan, "Hey \x02%s\x0F!" % nick)

def cmd_git(nick, host, chan, msg): # commands to interface with the bot's git repository
    if host not in ADMINS:
        say(chan, "\x02%s\x0F: you must be a bot admin to use this command." % nick)
        return

    args = get_args(msg)
    if not args:
        say(chan, "\x02%s\x0F: no arguments provided." % nick)
        return

    if args[0] == "help": # display all commands
        cmds = ["\x0303branch\x0301 (show current branch)", "\x0303branches\x0301 (show all branches)",
        "\x0303checkout\x0301 (switch branches)", "\x0303pull\x0301 (update current branch)"]
        cmds = ', '.join(cmds)
        say(chan, "\x02%s\x0F: sub-commands are: %s" % (nick, cmds))

    elif args[0] == "branch": # get our current branch
        branch = subprocess.check_output(['git', 'name-rev', '--name-only', 'HEAD'], stderr=subprocess.STDOUT) # git name-rev --name-only HEAD
        branch = branch[:-1] # strip newline
        say(chan, "\x02%s\x0F: currently on branch \x0302%s\x0301." % (nick, branch))

    elif args[0] == "branches": # get list of branches
        branches = subprocess.check_output(['git', 'branch'], stderr=subprocess.STDOUT) # git branch
        branches = branches[:-1] # strip newline
        branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
        branches = branches.replace('* ', ' ')
        branches = branches.replace('\n  ', ', ')
        branches = branches.strip()
        say(chan, "\x02%s\x0F: branches: \x0302%s\x0301." % (nick, branches))

    elif args[0] == "checkout": # switch branches
        try:
            branch = args[1]
        except IndexError: # no branch name provided
            say(chan, "\x02%s\x0F: switch to which branch?" % nick)
            return
        try:
            result = subprocess.check_output(['git', 'checkout', branch], stderr=subprocess.STDOUT) # git checkout our_branch
            if "Already on" in result:
                say(chan, "\x02%s\x0F: already on \x0302%s\x0301!" % (nick, branch))
            else:
                say(chan, "\x02%s\x0F: switched to branch \x0302%s\x0301." % (nick, branch))
        except subprocess.CalledProcessError: # git couldn't switch branches
            say(chan, "\x02%s\x0F: branch \x0302%s\x0301 does not exist!" % (nick, branch))

    elif args[0] == "pull": # pull from remote repository
        branch = subprocess.check_output(['git', 'name-rev', '--name-only', 'HEAD'], stderr=subprocess.STDOUT) # git name-rev --name-only HEAD
        branch = branch[:-1] # strip newline
        say(chan, "\x02%s\x0F: pulling from remote (currently on \x0302%s\x0301)..." % (nick, branch))
        result = subprocess.check_output(['git', 'pull']) # pull from remote
        if "Already up-to-date." in result:
            say(chan, "\x02%s\x0F: done; no new changes." % nick)
        else:
            say(chan, "\x02%s\x0F: done; new changes merged." % nick)

    else:
        say(chan, "\x02%s\x0F: unknown argument: \x0303%s\x0301." % (nick, args[0]))
