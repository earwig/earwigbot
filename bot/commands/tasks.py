# -*- coding: utf-8  -*-

# Manage wiki tasks from IRC, and check on thread status.

import threading
import re

from irc.classes import BaseCommand, Data, KwargParseException
from wiki import task_manager
from core import config

class Tasks(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Manage wiki tasks from IRC, and check on thread status."

    def check(self, data):
        if data.is_command and data.command in ["tasks", "task", "threads", "tasklist"]:
            return True
        return False

    def process(self, data):
        self.data = data
        if data.host not in config.irc["permissions"]["owners"]:
            self.connection.reply(data, "at this time, you must be a bot owner to use this command.")
            return

        if not data.args:
            if data.command == "tasklist":
                self.do_list()
            else:
                self.connection.reply(data, "no arguments provided. Maybe you wanted '!{cmnd} list', '!{cmnd} start', or '!{cmnd} listall'?".format(cmnd=data.command))
            return

        if data.args[0] == "list":
            self.do_list()

        elif data.args[0] == "start":
            self.do_start()

        elif data.args[0] in ["listall", "all"]:
            self.do_listall()

        else: # they asked us to do something we don't know
            self.connection.reply(data, "unknown argument: \x0303{0}\x0301.".format(data.args[0]))

    def do_list(self):
        """With !tasks list (or abbreviation !tasklist), list all running
        threads. This includes the main threads, like the irc frontend and the
        watcher, and task threads."""
        threads = threading.enumerate()

        normal_threads = []
        task_threads = []

        for thread in threads:
            tname = thread.name
            if tname == "MainThread":
                tname = self.get_main_thread_name()
                normal_threads.append("\x0302{0}\x0301 (as main thread, id {1})".format(tname, thread.ident))
            elif tname in ["irc-frontend", "irc-watcher", "wiki-scheduler"]:
                normal_threads.append("\x0302{0}\x0301 (id {1})".format(tname, thread.ident))
            elif tname.startswith("reminder"):
                normal_threads.append("\x0302reminder\x0301 (until {0})".format(tname.replace("reminder ", "")))
            else:
                tname, start_time = re.findall("^(.*?) \((.*?)\)$", tname)[0]
                task_threads.append("\x0302{0}\x0301 (id {1}, since {2})".format(tname, thread.ident, start_time))

        if task_threads:
            msg = "\x02{0}\x0F threads active: {1}, and \x02{2}\x0F task threads: {3}.".format(len(threads), ', '.join(normal_threads), len(task_threads), ', '.join(task_threads))
        else:
            msg = "\x02{0}\x0F threads active: {1}, and \x020\x0F task threads.".format(len(threads), ', '.join(normal_threads))
        self.connection.reply(self.data, msg)

    def do_listall(self):
        """With !tasks listall or !tasks all, list all loaded tasks, and report
        whether they are currently running or idle."""
        tasks = task_manager.task_list.keys()
        threads = threading.enumerate()
        tasklist = []

        tasks.sort()

        for task in tasks:
            threads_running_task = [t for t in threads if t.name.startswith(task)]
            ids = map(lambda t: str(t.ident), threads_running_task)
            if not ids:
                tasklist.append("\x0302{0}\x0301 (idle)".format(task))
            elif len(ids) == 1:
                tasklist.append("\x0302{0}\x0301 (\x02active\x0F as id {1})".format(task, ids[0]))
            else:
                tasklist.append("\x0302{0}\x0301 (\x02active\x0F as ids {1})".format(task, ', '.join(ids)))

        tasklist = ", ".join(tasklist)

        msg = "{0} tasks loaded: {1}.".format(len(tasks), tasklist)
        self.connection.reply(self.data, msg)

    def do_start(self):
        """With !tasks start, start any loaded task by name with or without
        kwargs."""
        data = self.data

        try:
            task_name = data.args[1]
        except IndexError: # no task name given
            self.connection.reply(data, "what task do you want me to start?")
            return

        try:
            data.parse_kwargs()
        except KwargParseException, arg:
            self.connection.reply(data, "error parsing argument: \x0303{0}\x0301.".format(arg))
            return

        if task_name not in task_manager.task_list.keys(): # this task does not exist or hasn't been loaded
            self.connection.reply(data, "task could not be found; either wiki/tasks/{0}.py doesn't exist, or it wasn't loaded correctly.".format(task_name))
            return

        task_manager.start_task(task_name, **data.kwargs)
        self.connection.reply(data, "task \x0302{0}\x0301 started.".format(task_name))

    def get_main_thread_name(self):
        """Return the "proper" name of the MainThread; e.g. "irc-frontend" or
        "irc-watcher"."""
        if "irc_frontend" in config.components:
            return "irc-frontend"
        elif "wiki_schedule" in config.components:
            return "wiki-scheduler"
        else:
            return "irc-watcher"
