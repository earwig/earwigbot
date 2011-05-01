# -*- coding: utf-8  -*-

# Commands to interface with the bot's git repository; use '!git help' for sub-command list.

import shlex, subprocess, re

from config.irc import *
from irc.base_command import BaseCommand

class Git(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Commands to interface with the bot's git repository; use '!git help' for sub-command list."

    def check(self, data):
        if data.is_command and data.command == "git":
            return True
        return False

    def process(self, data):
        self.data = data
        if data.host not in OWNERS:
            self.connection.reply(data, "you must be a bot owner to use this command.")
            return

        if not data.args:
            self.connection.reply(data, "no arguments provided. Maybe you wanted '!git help'?")
            return

        if data.args[0] == "help":
            self.do_help()

        elif data.args[0] == "branch":
            self.do_branch()

        elif data.args[0] == "branches":
            self.do_branches()

        elif data.args[0] == "checkout":
            self.do_checkout()

        elif data.args[0] == "delete":
            self.do_delete()

        elif data.args[0] == "pull":
            self.do_pull()

        elif data.args[0] == "status":
            self.do_status()

        else: # they asked us to do something we don't know
            self.connection.reply(data, "unknown argument: \x0303%s\x0301." % data.args[0])

    def exec_shell(self, command):
        """execute a shell command and get the output"""
        command = shlex.split(command)
        result = subprocess.check_output(command, stderr=subprocess.STDOUT)
        if result:
            result = result[:-1] # strip newline
        return result

    def do_help(self):
        """display all commands"""
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
        help = ""
        for key in keys:
            help += "\x0303%s\x0301 (%s), " % (key, help_dict[key])
        help = help[:-2] # trim last comma and space
        self.connection.reply(self.data, "sub-commands are: %s." % help)

    def do_branch(self):
        """get our current branch"""
        branch = self.exec_shell("git name-rev --name-only HEAD")
        self.connection.reply(self.data, "currently on branch \x0302%s\x0301." % branch)

    def do_branches(self):
        """get list of branches"""
        branches = self.exec_shell("git branch")
        branches = branches.replace('\n* ', ', ') # cleanup extraneous characters
        branches = branches.replace('* ', ' ')
        branches = branches.replace('\n  ', ', ')
        branches = branches.strip()
        self.connection.reply(self.data, "branches: \x0302%s\x0301." % branches)

    def do_checkout(self):
        """switch branches"""
        try:
            branch = self.data.args[1]
        except IndexError: # no branch name provided
            self.connection.reply(self.data, "switch to which branch?")
            return

        try:
            result = self.exec_shell("git checkout %s" % branch)
            if "Already on" in result:
                self.connection.reply(self.data, "already on \x0302%s\x0301!" % branch)
            else:
                current_branch = self.exec_shell("git name-rev --name-only HEAD")
                self.connection.reply(self.data, "switched from branch \x0302%s\x0301 to \x0302%s\x0301." % (current_branch, branch))

        except subprocess.CalledProcessError: # git couldn't switch branches
            self.connection.reply(self.data, "branch \x0302%s\x0301 doesn't exist!" % branch)

    def do_delete(self):
        """delete a branch, while making sure that we are not on it"""
        try:
            delete_branch = self.data.args[1]
        except IndexError: # no branch name provided
            self.connection.reply(self.data, "delete which branch?")
            return

        current_branch = self.exec_shell("git name-rev --name-only HEAD")

        if current_branch == delete_branch:
            self.connection.reply(self.data, "you're currently on this branch; please checkout to a different branch before deleting.")
            return

        try:
            self.exec_shell("git branch -d %s" % delete_branch)
            self.connection.reply(self.data, "branch \x0302%s\x0301 has been deleted locally." % delete_branch)
        except subprocess.CalledProcessError: # git couldn't delete
            self.connection.reply(self.data, "branch \x0302%s\x0301 doesn't exist!" % delete_branch)

    def do_pull(self):
        """pull from remote repository"""
        branch = self.exec_shell("git name-rev --name-only HEAD")
        self.connection.reply(self.data, "pulling from remote (currently on \x0302%s\x0301)..." % branch)

        result = self.exec_shell("git pull")

        if "Already up-to-date." in result:
            self.connection.reply(self.data, "done; no new changes.")
        else:
            changes = re.findall("\s*((.*?)\sfile(.*?)tions?\(-\))", result)[0][0] # find the changes
            try:
                remote = self.exec_shell("git config --get branch.%s.remote" % branch)
                url = self.exec_shell("git config --get remote.%s.url" % remote)
                self.connection.reply(self.data, "done; %s. [from %s]" % (changes, url))
            except subprocess.CalledProcessError: # something in .git/config is not specified correctly, so we cannot get the remote's url
                self.connection.reply(self.data, "done; %s." % changes)

    def do_status(self):
        """check whether we have anything to pull"""
        last = self.exec_shell("git log -n 1 --pretty=\"%ar\"")
        self.connection.reply(self.data, "last commit was %s. Checking remote for updates..." % last)
        result = self.exec_shell("git fetch --dry-run")
        if not result:
            self.connection.reply(self.data, "local copy is up-to-date with remote.")
        else:
            self.connection.reply(self.data, "remote is ahead of local copy.")
