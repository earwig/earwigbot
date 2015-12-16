# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

import threading
import re

from earwigbot.commands import Command

class Threads(Command):
    """Manage wiki tasks from IRC, and check on thread status."""
    name = "threads"
    commands = ["tasks", "task", "threads", "tasklist"]

    def process(self, data):
        self.data = data
        if not self.config.irc["permissions"].is_owner(data):
            msg = "You must be a bot owner to use this command."
            self.reply(data, msg)
            return

        if not data.args:
            if data.command == "tasklist":
                self.do_list()
            else:
                msg = "No arguments provided. Maybe you wanted '!{0} list', '!{0} start', or '!{0} listall'?"
                self.reply(data, msg.format(data.command))
            return

        if data.args[0] == "list":
            self.do_list()

        elif data.args[0] == "start":
            self.do_start()

        elif data.args[0] in ["listall", "all"]:
            self.do_listall()

        else:  # They asked us to do something we don't know
            msg = "Unknown argument: \x0303{0}\x0F.".format(data.args[0])
            self.reply(data, msg)

    def do_list(self):
        """With !tasks list (or abbreviation !tasklist), list all running
        threads. This includes the main threads, like the irc frontend and the
        watcher, and task threads."""
        threads = threading.enumerate()

        normal_threads = []
        daemon_threads = []

        for thread in threads:
            tname = thread.name
            ident = thread.ident % 10000
            if tname == "MainThread":
                t = "\x0302main\x0F (id {0})"
                normal_threads.append(t.format(ident))
            elif tname in self.config.components:
                t = "\x0302{0}\x0F (id {1})"
                normal_threads.append(t.format(tname, ident))
            elif tname.startswith("cvworker-"):
                t = "\x0302copyvio worker\x0F (site {0})"
                daemon_threads.append(t.format(tname[len("cvworker-"):]))
            else:
                match = re.findall("^(.*?) \((.*?)\)$", tname)
                if match:
                    t = "\x0302{0}\x0F (id {1}, since {2})"
                    thread_info = t.format(match[0][0], ident, match[0][1])
                    daemon_threads.append(thread_info)
                else:
                    t = "\x0302{0}\x0F (id {1})"
                    daemon_threads.append(t.format(tname, ident))

        if daemon_threads:
            if len(daemon_threads) > 1:
                msg = "\x02{0}\x0F threads active: {1}, and \x02{2}\x0F command/task threads: {3}."
            else:
                msg = "\x02{0}\x0F threads active: {1}, and \x02{2}\x0F command/task thread: {3}."
            msg = msg.format(len(threads), ', '.join(normal_threads),
                             len(daemon_threads), ', '.join(daemon_threads))
        else:
            msg = "\x02{0}\x0F threads active: {1}, and \x020\x0F command/task threads."
            msg = msg.format(len(threads), ', '.join(normal_threads))

        self.reply(self.data, msg)

    def do_listall(self):
        """With !tasks listall or !tasks all, list all loaded tasks, and report
        whether they are currently running or idle."""
        threads = threading.enumerate()
        tasklist = []
        for task in sorted([task.name for task in self.bot.tasks]):
            threadlist = [t for t in threads if t.name.startswith(task)]
            ids = [str(t.ident) for t in threadlist]
            if not ids:
                tasklist.append("\x0302{0}\x0F (idle)".format(task))
            elif len(ids) == 1:
                t = "\x0302{0}\x0F (\x02active\x0F as id {1})"
                tasklist.append(t.format(task, ids[0]))
            else:
                t = "\x0302{0}\x0F (\x02active\x0F as ids {1})"
                tasklist.append(t.format(task, ', '.join(ids)))

        tasks = ", ".join(tasklist)

        msg = "\x02{0}\x0F tasks loaded: {1}.".format(len(tasklist), tasks)
        self.reply(self.data, msg)

    def do_start(self):
        """With !tasks start, start any loaded task by name with or without
        kwargs."""
        data = self.data

        try:
            task_name = data.args[1]
        except IndexError:  # No task name given
            self.reply(data, "What task do you want me to start?")
            return

        if task_name not in [task.name for task in self.bot.tasks]:
            # This task does not exist or hasn't been loaded:
            msg = "Task could not be found; either it doesn't exist, or it wasn't loaded correctly."
            self.reply(data, msg.format(task_name))
            return

        data.kwargs["fromIRC"] = True
        data.kwargs["_IRCCallback"] = lambda: self.reply(
            data, "Task \x0302{0}\x0F finished.".format(task_name))

        self.bot.tasks.start(task_name, **data.kwargs)
        msg = "Task \x0302{0}\x0F started.".format(task_name)
        self.reply(data, msg)
