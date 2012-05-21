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
from threading import RLock, Thread
from time import gmtime, strftime

from earwigbot.commands import BaseCommand
from earwigbot.tasks import BaseTask

__all__ = ["CommandManager", "TaskManager"]

class _ResourceManager(object):
    """
    **EarwigBot: Resource Manager**

    Resources are essentially objects dynamically loaded by the bot, both
    packaged with it (built-in resources) and created by users (plugins, aka
    custom resources). Currently, the only two types of resources are IRC
    commands and bot tasks. These are both loaded from two locations: the
    :py:mod:`earwigbot.commands` and :py:mod:`earwigbot.tasks packages`, and
    the :file:`commands/` and :file:`tasks/` directories within the bot's
    working directory.

    This class handles the low-level tasks of (re)loading resources via
    :py:meth:`load`, retrieving specific resources via :py:meth:`get`, and
    iterating over all resources via :py:meth:`__iter__`.
    """
    def __init__(self, bot, name, attribute, base):
        self.bot = bot
        self.logger = bot.logger.getChild(name)

        self._resources = {}
        self._resource_name = name  # e.g. "commands" or "tasks"
        self._resource_attribute = attribute  # e.g. "Command" or "Task"
        self._resource_base = base  # e.g. BaseCommand or BaseTask
        self._resource_access_lock = RLock()

    def __iter__(self):
        with self.lock:
            for resource in self._resources.itervalues():
                yield resource

    def _load_resource(self, name, path):
        """Load a specific resource from a module, identified by name and path.

        We'll first try to import it using imp magic, and if that works, make
        an instance of the 'Command' class inside (assuming it is an instance
        of BaseCommand), add it to self._commands, and log the addition. Any
        problems along the way will either be ignored or logged.
        """
        f, path, desc = imp.find_module(name, [path])
        try:
            module = imp.load_module(name, f, path, desc)
        except Exception:
            e = "Couldn't load module {0} (from {1})"
            self.logger.exception(e.format(name, path))
            return
        finally:
            f.close()

        attr = self._resource_attribute
        if not hasattr(module, attr):
            return  # No resources in this module
        resource_class = getattr(module, attr)
        try:
            resource = resource_class(self.bot)  # Create instance of resource
        except Exception:
            e = "Error instantiating {0} class in {1} (from {2})"
            self.logger.exception(e.format(attr, name, path))
            return
        if not isinstance(resource, self._resource_base):
            return

        self._resources[resource.name] = resource
        self.logger.debug("Loaded {0} {1}".format(attr.lower(), resource.name))

    def _load_directory(self, dir):
        """Load all valid resources in a given directory."""
        processed = []
        for name in listdir(dir):
            if not name.endswith(".py") and not name.endswith(".pyc"):
                continue
            if name.startswith("_") or name.startswith("."):
                continue
            modname = sub("\.pyc?$", "", name)  # Remove extension
            if modname not in processed:
                self._load_resource(modname, dir)
                processed.append(modname)

    @property
    def lock(self):
        """The resource access/modify lock."""
        return self._resource_access_lock

    def load(self):
        """Load (or reload) all valid resources into :py:attr:`_resources`."""
        name = self._resource_name  # e.g. "commands" or "tasks"
        with self.lock:
            self._resources.clear()
            builtin_dir = path.join(path.dirname(__file__), name)
            plugins_dir = path.join(self.bot.config.root_dir, name)
            self._load_directory(builtin_dir)  # Built-in resources
            self._load_directory(plugins_dir)  # Custom resources, aka plugins

        msg = "Loaded {0} {1}: {2}"
        resources = ", ".join(self._resources.keys())
        self.logger.info(msg.format(len(self._resources), name, resources))

    def get(self, key):
        """Return the class instance associated with a certain resource.

        Will raise :py:exc:`KeyError` if the resource (a command or task) is
        not found.
        """
        with self.lock:
            return self._resources[key]


class CommandManager(_ResourceManager):
    """
    Manages (i.e., loads, reloads, and calls) IRC commands.
    """
    def __init__(self, bot):
        base = super(CommandManager, self)
        base.__init__(bot, "commands", "Command", BaseCommand)

    def _wrap_check(self, command, data):
        """Check whether a command should be called, catching errors."""
        try:
            return command.check(data)
        except Exception:
            e = "Error checking command '{0}' with data: {1}:"
            self.logger.exception(e.format(command.name, data))

    def _wrap_process(self, command, data):
        """process() the message, catching and reporting any errors."""
        try:
            command.process(data)
        except Exception:
            e = "Error executing command '{0}':"
            self.logger.exception(e.format(command.name))

    def call(self, hook, data):
        """Respond to a hook type and a :py:class:`Data` object."""
        for command in self:
            if hook in command.hooks and self._wrap_check(command, data):
                self._wrap_process(command, data)
                return


class TaskManager(_ResourceManager):
    """
    Manages (i.e., loads, reloads, schedules, and runs) wiki bot tasks.
    """
    def __init__(self, bot):
        super(TaskManager, self).__init__(bot, "tasks", "Task", BaseTask)

    def _wrapper(self, task, **kwargs):
        """Wrapper for task classes: run the task and catch any errors."""
        try:
            task.run(**kwargs)
        except Exception:
            msg = "Task '{0}' raised an exception and had to stop:"
            self.logger.exception(msg.format(task.name))
        else:
            msg = "Task '{0}' finished successfully"
            self.logger.info(msg.format(task.name))

    def start(self, task_name, **kwargs):
        """Start a given task in a new daemon thread, and return the thread.

        kwargs are passed to :py:meth:`task.run() <earwigbot.tasks.BaseTask>`.
        If the task is not found, ``None`` will be returned an an error is
        logged.
        """
        msg = "Starting task '{0}' in a new thread"
        self.logger.info(msg.format(task_name))

        try:
            task = self.get(task_name)
        except KeyError:
            e = "Couldn't find task '{0}'"
            self.logger.error(e.format(task_name))
            return

        task_thread = Thread(target=self._wrapper, args=(task,), kwargs=kwargs)
        start_time = strftime("%b %d %H:%M:%S")
        task_thread.name = "{0} ({1})".format(task_name, start_time)
        task_thread.daemon = True
        task_thread.start()
        return task_thread

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
