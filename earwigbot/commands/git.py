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

import time

import git

from earwigbot.commands import Command

class Git(Command):
    """Commands to interface with the bot's git repository; use '!git' for a
    sub-command list."""
    name = "git"

    def setup(self):
        try:
            self.repos = self.config.commands[self.name]["repos"]
        except KeyError:
            self.repos = None

    def process(self, data):
        self.data = data
        if data.host not in self.config.irc["permissions"]["owners"]:
            msg = "you must be a bot owner to use this command."
            self.reply(data, msg)
            return
        if not data.args or data.args[0] == "help":
            self.do_help()
            return
        if not self.repos:
            self.reply(data, "no repos are specified in the config file.")
            return

        command = data.args[0]
        try:
            repo_name = data.args[1]
        except IndexError:
            repos = self.get_repos()
            msg = "which repo do you want to work with (options are {0})?"
            self.reply(data, msg.format(repos))
            return
        if repo_name not in self.repos:
            repos = self.get_repos()
            msg = "repository must be one of the following: {0}."
            self.reply(data, msg.format(repos))
            return
        self.repo = git.Repo(self.repos[repo_name])

        if command == "branch":
            self.do_branch()
        elif command == "branches":
            self.do_branches()
        elif command == "checkout":
            self.do_checkout()
        elif command == "delete":
            self.do_delete()
        elif command == "pull":
            self.do_pull()
        elif command == "status":
            self.do_status()
        else:  # They asked us to do something we don't know
            msg = "unknown argument: \x0303{0}\x0301.".format(data.args[0])
            self.reply(data, msg)

    def get_repos(self):
        data = self.repos.iteritems()
        repos = ["\x0302{0}\x0301 ({1})".format(k, v) for k, v in data]
        return ", ".join(repos)

    def get_remote(self):
        try:
            remote_name = self.data.args[2]
        except IndexError:
            remote_name = "origin"
        try:
            return getattr(self.repo.remotes, remote_name)
        except AttributeError:
            msg = "unknown remote: \x0302{0}\x0301.".format(remote_name)
            self.reply(self.data, msg)

    def get_time_since(self, date):
        diff = time.mktime(time.gmtime()) - date
        if diff < 60:
            return "{0} seconds".format(int(diff))
        if diff < 60 * 60:
            return "{0} minutes".format(int(diff / 60))
        if diff < 60 * 60 * 24:
            return "{0} hours".format(int(diff / 60 / 60))
        return "{0} days".format(int(diff / 60 / 60 / 24))

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
        subcommands = ""
        for key in sorted(help.keys()):
            subcommands += "\x0303{0}\x0301 ({1}), ".format(key, help[key])
        subcommands = subcommands[:-2]  # Trim last comma and space
        msg = "sub-commands are: {0}; repos are: {1}. Syntax: !git \x0303subcommand\x0301 \x0302repo\x0301."
        self.reply(self.data, msg.format(subcommands, self.get_repos()))

    def do_branch(self):
        """Get our current branch."""
        branch = self.repo.active_branch.name
        msg = "currently on branch \x0302{0}\x0301.".format(branch)
        self.reply(self.data, msg)

    def do_branches(self):
        """Get a list of branches."""
        branches = [branch.name for branch in self.repo.branches]
        msg = "branches: \x0302{0}\x0301.".format(", ".join(branches))
        self.reply(self.data, msg)

    def do_checkout(self):
        """Switch branches."""
        try:
            target = self.data.args[2]
        except IndexError:  # No branch name provided
            self.reply(self.data, "switch to which branch?")
            return

        current_branch = self.repo.active_branch.name
        if target == current_branch:
            msg = "already on \x0302{0}\x0301!".format(target)
            self.reply(self.data, msg)
            return

        try:
            ref = getattr(self.repo.branches, target)
        except AttributeError:
            msg = "branch \x0302{0}\x0301 doesn't exist!".format(target)
            self.reply(self.data, msg)
        else:
            ref.checkout()
            ms = "switched from branch \x0302{0}\x0301 to \x0302{1}\x0301."
            msg = ms.format(current_branch, target)
            self.reply(self.data, msg)
            log = "{0} checked out branch {1} of {2}"
            logmsg = log.format(self.data.nick, target, self.repo.working_dir)
            self.logger.info(logmsg)

    def do_delete(self):
        """Delete a branch, while making sure that we are not already on it."""
        try:
            target = self.data.args[2]
        except IndexError:  # No branch name provided
            self.reply(self.data, "delete which branch?")
            return

        current_branch = self.repo.active_branch.name
        if current_branch == target:
            msg = "you're currently on this branch; please checkout to a different branch before deleting."
            self.reply(self.data, msg)
            return

        try:
            ref = getattr(self.repo.branches, target)
        except AttributeError:
            msg = "branch \x0302{0}\x0301 doesn't exist!".format(target)
            self.reply(self.data, msg)
        else:
            self.repo.git.branch("-d", ref)
            msg = "branch \x0302{0}\x0301 has been deleted locally."
            self.reply(self.data, msg.format(target))
            log = "{0} deleted branch {1} of {2}"
            logmsg = log.format(self.data.nick, target, self.repo.working_dir)
            self.logger.info(logmsg)

    def do_pull(self):
        """Pull from our remote repository."""
        branch = self.repo.active_branch.name
        msg = "pulling from remote (currently on \x0302{0}\x0301)..."
        self.reply(self.data, msg.format(branch))

        remote = self.get_remote()
        if not remote:
            return
        result = remote.pull()
        updated = [info for info in result if info.flags != info.HEAD_UPTODATE]

        if updated:
            branches = ", ".join([info.ref.remote_head for info in updated])
            msg = "done; updates to \x0302{0}\x0301 (from {1})."
            self.reply(self.data, msg.format(branches, remote.url))
            log = "{0} pulled {1} of {2} (updates to {3})"
            self.logger.info(log.format(self.data.nick, remote.name,
                                        self.repo.working_dir, branches))
        else:
            self.reply(self.data, "done; no new changes.")
            log = "{0} pulled {1} of {2} (no updates)"
            self.logger.info(log.format(self.data.nick, remote.name,
                                        self.repo.working_dir))

    def do_status(self):
        """Check if we have anything to pull."""
        remote = self.get_remote()
        if not remote:
            return
        since = self.get_time_since(self.repo.head.object.committed_date)
        result = remote.fetch(dry_run=True)
        updated = [info for info in result if info.flags != info.HEAD_UPTODATE]

        if updated:
            branches = ", ".join([info.ref.remote_head for info in updated])
            msg = "last local commit was \x02{0}\x0F ago; updates to \x0302{1}\x0301."
            self.reply(self.data, msg.format(since, branches))
            log = "{0} got status of {1} of {2} (updates to {3})"
            self.logger.info(log.format(self.data.nick, remote.name,
                                        self.repo.working_dir, branches))
        else:
            msg = "last commit was \x02{0}\x0F ago. Local copy is up-to-date with remote."
            self.reply(self.data, msg.format(since))
            log = "{0} pulled {1} of {2} (no updates)"
            self.logger.info(log.format(self.data.nick, remote.name,
                                        self.repo.working_dir))
