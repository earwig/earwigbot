#! /usr/bin/env python
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

import imp
from os import listdir, path
from re import sub
from threading import Lock, Thread
from time import gmtime, strftime

from earwigbot.commands import BaseCommand
from earwigbot.tasks import BaseTask

__all__ = ["CommandManager", "TaskManager"]

class _BaseManager(object):
    pass


class CommandManager(_BaseManager):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild("commands")
        self._commands = {}
        self._command_access_lock = Lock()

    def __iter__(self):
        for name in self._commands:
            yield name

    def _load_command(self, name, path):
        """Load a specific command from a module, identified by name and path.

        We'll first try to import it using imp magic, and if that works, make
        an instance of the 'Command' class inside (assuming it is an instance
        of BaseCommand), add it to self._commands, and log the addition. Any
        problems along the way will either be ignored or logged.
        """
        f, path, desc = imp.find_module(name, [path])
        try:
             module = imp.load_module(name, f, path, desc)
        except Exception:
            e = "Couldn't load module {0} from {1}"
            self.logger.exception(e.format(name, path))
            return
        finally:
            f.close()

        try:
            command_class = module.Command
        except AttributeError:
            return  # No command in this module
        try:
            command = command_class(self.bot)
        except Exception:
            e = "Error initializing Command() class in {0} (from {1})"
            self.logger.exception(e.format(name, path))
            return
        if not isinstance(command, BaseCommand):
            return

        self._commands[command.name] = command
        self.logger.debug("Loaded command {0}".format(command.name))

    def _load_directory(self, dir):
        """Load all valid commands in a given directory."""
        processed = []
        for name in listdir(dir):
            if not name.endswith(".py") and not name.endswith(".pyc"):
                continue
            if name.startswith("_") or name.startswith("."):
                continue
            modname = sub("\.pyc?$", "", name)  # Remove extension
            if modname not in processed:
                self._load_command(modname, dir)
                processed.append(modname)

    def load(self):
        """Load (or reload) all valid commands into self._commands."""
        with self._command_access_lock:
            self._commands.clear()
            builtin_dir = path.join(path.dirname(__file__), "commands")
            plugins_dir = path.join(self.bot.config.root_dir, "commands")
            self._load_directory(builtin_dir)  # Built-in commands
            self._load_directory(plugins_dir)  # Custom commands, aka plugins

        msg = "Loaded {0} commands: {1}"
        commands = ", ".join(self._commands.keys())
        self.logger.info(msg.format(len(self._commands), commands))

    def check(self, hook, data):
        """Given an IRC event, check if there's anything we can respond to."""
        with self._command_access_lock:
            for command in self._commands.values():
                if hook in command.hooks:
                    if command.check(data):
                        try:
                            command._wrap_process(data)
                        except Exception:
                            e = "Error executing command '{0}':"
                            self.logger.exception(e.format(data.command))
                        break

    def get(self, command_name):
        """Return the class instance associated with a certain command name.

        Will raise KeyError if the command is not found.
        """
        return self._command[command_name]


class TaskManager(_BaseManager):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild("tasks")
        self._tasks = {}
        self._task_access_lock = Lock()

    def __iter__(self):
        for name in self._tasks:
            yield name

    def _wrapper(self, task, **kwargs):
        """Wrapper for task classes: run the task and catch any errors."""
        try:
            task.run(**kwargs)
        except Exception:
            msg = "Task '{0}' raised an exception and had to stop:"
            self.logger.exception(msg.format(task.name))
        else:
            msg = "Task '{0}' finished without error"
            self.logger.info(msg.format(task.name))

    def _load_task(self, name, path):
        """Load a specific task from a module, identified by name and path.

        We'll first try to import it using imp magic, and if that works, make
        an instance of the 'Task' class inside (assuming it is an instance of
        BaseTask), add it to self._tasks, and log the addition. Any problems
        along the way will either be ignored or logged.
        """
        f, path, desc = imp.find_module(name, [path])
        try:
             module = imp.load_module(name, f, path, desc)
        except Exception:
            e = "Couldn't load module {0} from {1}"
            self.logger.exception(e.format(name, path))
            return
        finally:
            f.close()

        try:
            task_class = module.Task
        except AttributeError:
            return  # No task in this module
        try:
            task = task_class(self.bot)
        except Exception:
            e = "Error initializing Task() class in {0} (from {1})"
            self.logger.exception(e.format(name, path))
            return
        if not isinstance(task, BaseTask):
            return

        self._tasks[task.name] = task
        self.logger.debug("Loaded task {0}".format(task.name))

    def _load_directory(self, dir):
        """Load all valid tasks in a given directory."""
        processed = []
        for name in listdir(dir):
            if not name.endswith(".py") and not name.endswith(".pyc"):
                continue
            if name.startswith("_") or name.startswith("."):
                continue
            modname = sub("\.pyc?$", "", name)  # Remove extension
            if modname not in processed:
                self._load_task(modname, dir)
                processed.append(modname)

    def load(self):
        """Load (or reload) all valid tasks into self._tasks."""
        with self._task_access_lock:
            self._tasks.clear()
            builtin_dir = path.join(path.dirname(__file__), "tasks")
            plugins_dir = path.join(self.bot.config.root_dir, "tasks")
            self._load_directory(builtin_dir)  # Built-in tasks
            self._load_directory(plugins_dir)  # Custom tasks, aka plugins

        msg = "Loaded {0} tasks: {1}"
        tasks = ', '.join(self._tasks.keys())
        self.logger.info(msg.format(len(self._tasks), tasks))

    def start(self, task_name, **kwargs):
        """Start a given task in a new thread. kwargs are passed to task.run"""
        msg = "Starting task '{0}' in a new thread"
        self.logger.info(msg.format(task_name))

        with self._task_access_lock:
            try:
                task = self._tasks[task_name]
            except KeyError:
                e = "Couldn't find task '{0}':"
                self.logger.error(e.format(task_name))
                return

        task_thread = Thread(target=self._wrapper, args=(task,), kwargs=kwargs)
        start_time = strftime("%b %d %H:%M:%S")
        task_thread.name = "{0} ({1})".format(task_name, start_time)
        task_thread.start()

    def schedule(self, now=None):
        """Start all tasks that are supposed to be run at a given time."""
        if not now:
            now = gmtime()
        # Get list of tasks to run this turn:
        tasks = self.bot.config.schedule(now.tm_min, now.tm_hour, now.tm_mday,
                                         now.tm_mon, now.tm_wday)

        for task in tasks:
            if isinstance(task, list):          # They've specified kwargs,
                self.start(task[0], **task[1])  # so pass those to start
            else:  # Otherwise, just pass task_name
                self.start(task)

    def get(self, task_name):
        """Return the class instance associated with a certain task name.

        Will raise KeyError if the task is not found.
        """
        return self._tasks[task_name]
