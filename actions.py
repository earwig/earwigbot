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
    say(chan, "'sup %s?" % nick)

def cmd_git(nick, host, chan, msg): # commands to interface with the bot's git repository
    if host not in ADMINS:
        say(chan, "%s: you must be a bot admin to use this command." % nick)
        return

    args = get_args(msg)
    if not args:
        say(chan, "%s: no arguments provided." % nick)
        return

    if args[0] == "help": # display all commands
        cmds = ["branch (show current branch)", "branches (show all branches)", "checkout (switch branches)", "pull (update current branch)"]
        cmds = ', '.join(cmds)
        say(chan, "%s: sub-commands are: %s" % (nick, cmds))

    elif args[0] == "branch": # get our current branch
        branch = subprocess.check_output(['git', 'name-rev', '--name-only', 'HEAD'], stderr=subprocess.STDOUT) # git name-rev --name-only HEAD
        branch = branch[:-1] # strip newline
        say(chan, "%s: currently on branch '%s'." % (nick, branch))

    elif args[0] == "branches": # get list of branches
        branches = subprocess.check_output(['git', 'branch'], stderr=subprocess.STDOUT) # git branch
        branches = branches[:-1] # strip newline
        branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
        branches = branches.replace('* ', ' ')
        branches = branches.replace('\n  ', ', ')
        branches = branches.strip()
        say(chan, "%s: branches: %s." % (nick, branches))

    elif args[0] == "checkout": # switch branches
        try:
            branch = args[1]
        except IndexError: # no branch name provided
            say(chan, "%s: switch to which branch?" % nick)
            return
        try:
            result = subprocess.check_output(['git', 'checkout', branch], stderr=subprocess.STDOUT) # git checkout our_branch
            result = result[:-1] # strip newline
            result = string.lower(result[0] + result[1:]) # lowercase first word
            say(chan, "%s: %s." % (nick, result))
        except subprocess.CalledProcessError: # git couldn't switch branches
            say(chan, "%s: branch '%s' does not exist!" % (nick, branch))

    elif args[0] == "pull": # pull from remote repository
        branch = subprocess.check_output(['git', 'name-rev', '--name-only', 'HEAD'], stderr=subprocess.STDOUT) # git name-rev --name-only HEAD
        branch = branch[:-1] # strip newline
        say(chan, "%s: pulling branch '%s' from remote..." % (nick, branch))
        result = subprocess.check_output(['git', 'pull', 'origin', branch]) # pull from remote
        if "Already up-to-date." in result:
            say(chan, "%s: done; no new changes." % nick)
        else:
            say(chan, "%s: done; new changes merged." % nick)

    else:
        say(chan, "%s: unknown argument: '%s'." % (nick, arg[0]))
