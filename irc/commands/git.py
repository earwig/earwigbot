# -*- coding: utf-8  -*-

"""Commands to interface with the bot's git repository; use '!git help' for sub-command list."""

import shlex, subprocess, re
from config.irc_config import *

connection, data = None, None

def call(c, d):
    global connection, data
    connection, data = c, d

    if data.host not in ADMINS:
        connection.reply(data.chan, data.nick, "you must be a bot admin to use this command.")
        return
    
    if not data.args:
        connection.reply(data.chan, data.nick, "no arguments provided.")
        return

    if data.args[0] == "help":
        do_help()

    elif data.args[0] == "branch":
        do_branch()

    elif data.args[0] == "branches":
        do_branches()

    elif data.args[0] == "checkout":
        do_checkout()

    elif data.args[0] == "delete":
        do_delete()

    elif data.args[0] == "pull":
        do_pull()

    elif data.args[0] == "status":
        do_status()

    else: # they asked us to do something we don't know
        connection.reply(data.chan, data.nick, "unknown argument: \x0303%s\x0301." % data.args[0])

def exec_shell(command):
    """execute a shell command and get the output"""
    command = shlex.split(command)
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    return result

def do_help():
    """display all commands"""
    help = ""

    help_dict = {
        "branch": "get current branch",
        "branches": "get all branches",
        "checkout": "switch branches",
        "delete": "delete an old branch",
        "pull": "update everything from the remote server",
        "status": "check if we are up-to-date",
    }

    keys = help_dict.keys()
    keys.sort()
    for key in keys:
        help += "\x0303%s\x0301 (%s), " % (key, help_dict[key])
    help = help[:-2] # trim last comma

    connection.reply(data.chan, data.nick, "sub-commands are: %s." % help)

def do_branch():
    """get our current branch"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline

    connection.reply(data.chan, data.nick, "currently on branch \x0302%s\x0301." % branch)

def do_branches():
    """get list of branches"""
    branches = exec_shell("git branch")

    branches = branches[:-1] # strip newline
    branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
    branches = branches.replace('* ', ' ')
    branches = branches.replace('\n  ', ', ')
    branches = branches.strip()

    connection.reply(data.chan, data.nick, "branches: \x0302%s\x0301." % branches)

def do_checkout():
    """switch branches"""
    try:
        branch = data.args[1]
    except IndexError: # no branch name provided
        connection.reply(data.chan, data.nick, "switch to which branch?")
        return

    try:
        result = exec_shell("git checkout %s" % branch)
        if "Already on" in result:
            connection.reply(data.chan, data.nick, "already on \x0302%s\x0301!" % branch)
        else:
            connection.reply(data.chan, data.nick, "switched to branch \x0302%s\x0301." % branch)

    except subprocess.CalledProcessError: # git couldn't switch branches
        connection.reply(data.chan, data.nick, "branch \x0302%s\x0301 doesn't exist!" % branch)

def do_delete():
    """delete a branch, while making sure that we are not on it"""
    try:
        delete_branch = data.args[1]
    except IndexError: # no branch name provided
        connection.reply(data.chan, data.nick, "delete which branch?")
        return

    current_branch = exec_shell("git name-rev --name-only HEAD")
    current_branch = current_branch[:-1] # strip newline

    if current_branch == delete_branch:
        connection.reply(data.chan, data.nick, "you're currently on this branch; please checkout to a different branch before deleting.")
        return

    try:
        exec_shell("git branch -d %s" % delete_branch)
        connection.reply(data.chan, data.nick, "branch \x0302%s\x0301 has been deleted locally." % delete_branch)
    except subprocess.CalledProcessError: # git couldn't delete
        connection.reply(data.chan, data.nick, "branch \x0302%s\x0301 doesn't exist!" % delete_branch)

def do_pull():
    """pull from remote repository"""
    branch = exec_shell("git name-rev --name-only HEAD")
    branch = branch[:-1] # strip newline
    connection.reply(data.chan, data.nick, "pulling from remote (currently on \x0302%s\x0301)..." % branch)

    result = exec_shell("git pull")

    if "Already up-to-date." in result:
        connection.reply(data.chan, data.nick, "done; no new changes.")
    else:
        changes = re.findall("\s*((.*?)\sfile(.*?)tions?\(-\))", result)[0][0] # find the changes
        connection.reply(data.chan, data.nick, "done; %s." % changes)

def do_status():
    """check whether we have anything to pull"""
    connection.reply(data.chan, data.nick, "checking remote for updates...")
    result = exec_shell("git fetch --dry-run")
    if not result:
        connection.reply(data.chan, data.nick, "local copy is up-to-date with remote.")
    else:
        connection.reply(data.chan, data.nick, "remote is ahead of local copy.")
