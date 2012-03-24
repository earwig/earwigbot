# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import shlex
import subprocess
import re

from earwigbot.commands import BaseCommand
from earwigbot.config import config

class Command(BaseCommand):
    """Commands to interface with the bot's git repository; use '!git' for a
    sub-command list."""
    name = "git"

    def process(self, data):
        self.data = data
        if data.host not in config.irc["permissions"]["owners"]:
            msg = "you must be a bot owner to use this command."
            self.connection.reply(data, msg)
            return

        if not data.args:
            self.do_help()
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

        else:  # They asked us to do something we don't know
            msg = "unknown argument: \x0303{0}\x0301.".format(data.args[0])
            self.connection.reply(data, msg)

    def exec_shell(self, command):
        """Execute a shell command and get the output."""
        command = shlex.split(command)
        result = subprocess.check_output(command, stderr=subprocess.STDOUT)
        if result:
            result = result[:-1]  # Strip newline
        return result

    def do_help(self):
        """Display all commands."""
        help = {
            "branch": "get current branch",
            "branches": "get all branches",
            "checkout": "switch branches",
            "delete": "delete an old branch",
            "pull": "update everything from the remote server",
            "status": "check if we are up-to-date",
        }
        msg = ""
        for key in sorted(help.keys()):
            msg += "\x0303{0}\x0301 ({1}), ".format(key, help[key])
        msg = msg[:-2]  # Trim last comma and space
        self.connection.reply(self.data, "sub-commands are: {0}.".format(msg))

    def do_branch(self):
        """Get our current branch."""
        branch = self.exec_shell("git name-rev --name-only HEAD")
        msg = "currently on branch \x0302{0}\x0301.".format(branch)
        self.connection.reply(self.data, msg)

    def do_branches(self):
        """Get a list of branches."""
        branches = self.exec_shell("git branch")
        # Remove extraneous characters:
        branches = branches.replace('\n* ', ', ')
        branches = branches.replace('* ', ' ')
        branches = branches.replace('\n  ', ', ')
        branches = branches.strip()
        msg = "branches: \x0302{0}\x0301.".format(branches)
        self.connection.reply(self.data, msg)

    def do_checkout(self):
        """Switch branches."""
        try:
            branch = self.data.args[1]
        except IndexError: # no branch name provided
            self.connection.reply(self.data, "switch to which branch?")
            return

        current_branch = self.exec_shell("git name-rev --name-only HEAD")

        try:
            result = self.exec_shell("git checkout %s" % branch)
            if "Already on" in result:
                msg = "already on \x0302{0}\x0301!".format(branch)
                self.connection.reply(self.data, msg)
            else:
                ms = "switched from branch \x0302{1}\x0301 to \x0302{1}\x0301."
                msg = ms.format(current_branch, branch)
                self.connection.reply(self.data, msg)

        except subprocess.CalledProcessError:
            # Git couldn't switch branches; assume the branch doesn't exist:
            msg = "branch \x0302{0}\x0301 doesn't exist!".format(branch)
            self.connection.reply(self.data, msg)

    def do_delete(self):
        """Delete a branch, while making sure that we are not already on it."""
        try:
            delete_branch = self.data.args[1]
        except IndexError: # no branch name provided
            self.connection.reply(self.data, "delete which branch?")
            return

        current_branch = self.exec_shell("git name-rev --name-only HEAD")

        if current_branch == delete_branch:
            msg = "you're currently on this branch; please checkout to a different branch before deleting."
            self.connection.reply(self.data, msg)
            return

        try:
            self.exec_shell("git branch -d %s" % delete_branch)
            msg = "branch \x0302{0}\x0301 has been deleted locally."
            self.connection.reply(self.data, msg.format(delete_branch))
        except subprocess.CalledProcessError:
            # Git couldn't switch branches; assume the branch doesn't exist:
            msg = "branch \x0302{0}\x0301 doesn't exist!".format(delete_branch)
            self.connection.reply(self.data, msg)

    def do_pull(self):
        """Pull from our remote repository."""
        branch = self.exec_shell("git name-rev --name-only HEAD")
        msg = "pulling from remote (currently on \x0302{0}\x0301)..."
        self.connection.reply(self.data, msg.format(branch))

        result = self.exec_shell("git pull")

        if "Already up-to-date." in result:
            self.connection.reply(self.data, "done; no new changes.")
        else:
            regex = "\s*((.*?)\sfile(.*?)tions?\(-\))"
            changes = re.findall(regex, result)[0][0]
            try:
                cmnd_remt = "git config --get branch.{0}.remote".format(branch)
                remote = self.exec_shell(cmnd_remt)
                cmnd_url = "git config --get remote.{0}.url".format(remote)
                url = self.exec_shell(cmnd_url)
                msg = "done; {0} [from {1}].".format(changes, url)
                self.connection.reply(self.data, msg)
            except subprocess.CalledProcessError:
                # Something in .git/config is not specified correctly, so we
                # cannot get the remote's URL. However, pull was a success:
                self.connection.reply(self.data, "done; %s." % changes)

    def do_status(self):
        """Check whether we have anything to pull."""
        last = self.exec_shell('git log -n 1 --pretty="%ar"')
        result = self.exec_shell("git fetch --dry-run")
        if not result:  # Nothing was fetched, so remote and local are equal
            msg = "last commit was {0}. Local copy is \x02up-to-date\x0F with remote."
            self.connection.reply(self.data, msg.format(last))
        else:
            msg = "last local commit was {0}. Remote is \x02ahead\x0F of local copy."
            self.connection.reply(self.data, msg.format(last))
