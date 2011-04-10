# -*- coding: utf-8  -*-

# Commands to interface with the bot's git repository.

import shlex, subprocess
from config.irc_config import *

actions, data = None, None
args = None

def call(a, d):
    global actions, data
    actions, data = a, d

    if not check_user_is_admin():
        return

    args = get_args()
    
    if not check_has_args():
        return

    if args[0] == "help":
        do_help()

    elif args[0] == "branch":
        do_branch()

    elif args[0] == "branches":
        do_branches()

    elif args[0] == "checkout":
        do_checkout()

    elif args[0] == "pull":
        do_pull()

    else:
        unknown_arg() # they asked us to do something we don't know

def get_args():
    """get command arguments"""
    args = data.msg.strip().split(' ') # strip out extra whitespace and split the message into a list
    while '' in args: # remove any empty arguments
        args.remove('')
    return args[1:] # remove the command itself

def check_user_is_admin():
    """check if the user is a bot admin (and can use this command, as a result)"""
    if data.host not in ADMINS:
        actions.say(data.chan, "\x02%s\x0F: you must be a bot admin to use this command." % data.nick)
        return False
    return True

def check_has_args():
    """check if they provided arguments along with the !git command"""
    if not args:
        actions.say(data.chan, "\x02%s\x0F: no arguments provided." % data.nick)
        return False
    return True

def exec_shell(command):
    """execute a shell command and get the output"""
    command = shlex.split(command)
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    return result

def do_help():
    """display all commands"""
    help = ["\x0303branch\x0301 (show current branch)", "\x0303branches\x0301 (show all branches)",
    "\x0303checkout\x0301 (switch branches)", "\x0303pull\x0301 (update current branch)"]
    help = ', '.join(help)

    actions.say(data.chan, "\x02%s\x0F: sub-commands are: %s" % (data.nick, help))

def do_branch():
    """get our current branch"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline

    actions.say(data.chan, "\x02%s\x0F: currently on branch \x0302%s\x0301." % (data.nick, branch))

def do_branches():
    """get list of branches"""
    branches = exec_shell("git branch")

    branches = branches[:-1] # strip newline
    branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
    branches = branches.replace('* ', ' ')
    branches = branches.replace('\n  ', ', ')
    branches = branches.strip()

    actions.say(data.chan, "\x02%s\x0F: branches: \x0302%s\x0301." % (data.nick, branches))

def do_checkout():
    """switch branches"""
    try:
        branch = args[1]
    except IndexError: # no branch name provided
        actions.say(chan, "\x02%s\x0F: switch to which branch?" % data.nick)
        return

    try:
        result = exec_shell("git checkout %s" % branch)
        if "Already on" in result:
            actions.say(data.chan, "\x02%s\x0F: already on \x0302%s\x0301!" % (data.nick, branch))
        else:
            actions.say(data.chan, "\x02%s\x0F: switched to branch \x0302%s\x0301." % (data.nick, branch))

    except subprocess.CalledProcessError: # git couldn't switch branches
        actions.say(data.chan, "\x02%s\x0F: branch \x0302%s\x0301 does not exist!" % (data.nick, branch))

def do_pull():
    """pull from remote repository"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline
    actions.say(data.chan, "\x02%s\x0F: pulling from remote (currently on \x0302%s\x0301)..." % (data.nick, branch))

    result = exec_shell("git pull")

    if "Already up-to-date." in result:
        actions.say(data.chan, "\x02%s\x0F: done; no new changes." % data.nick)
    else:
        actions.say(data.chan, "\x02%s\x0F: done; new changes merged." % data.nick)

def unknown_arg():
    actions.say(data.chan, "\x02%s\x0F: unknown argument: \x0303%s\x0301." % (data.nick, args[0]))
