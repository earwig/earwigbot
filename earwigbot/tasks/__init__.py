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

"""
EarwigBot's Wiki Task Manager

This package provides the wiki bot "tasks" EarwigBot runs. This module contains
the BaseTask class (import with `from earwigbot.tasks import BaseTask`) and an
internal TaskManager class.  This can be accessed through `bot.tasks`.
"""

import imp
from os import listdir, path
from re import sub
from threading import Lock, Thread
from time import gmtime, strftime

from earwigbot import wiki

__all__ = ["BaseTask", "TaskManager"]

class BaseTask(object):
    """A base class for bot tasks that edit Wikipedia."""
    name = None
    number = 0

    def __init__(self, bot):
        """Constructor for new tasks.

        This is called once immediately after the task class is loaded by
        the task manager (in tasks._load_task()). Don't override this directly
        (or if you do, remember super(Task, self).__init()) - use setup().
        """
        self.bot = bot
        self.config = bot.config
        self.logger = bot.tasks.logger.getChild(self.name)
        self.setup()

    def setup(self):
        """Hook called immediately after the task is loaded.

        Does nothing by default; feel free to override.
        """
        pass

    def run(self, **kwargs):
        """Main entry point to run a given task.

        This is called directly by tasks.start() and is the main way to make a
        task do stuff. kwargs will be any keyword arguments passed to start()
        which are entirely optional.

        The same task instance is preserved between runs, so you can
        theoretically store data in self (e.g.
        start('mytask', action='store', data='foo')) and then use it later
        (e.g. start('mytask', action='save')).
        """
        pass

    def make_summary(self, comment):
        """Makes an edit summary by filling in variables in a config value.

        config.wiki["summary"] is used, where $2 is replaced by the main
        summary body, given as a method arg, and $1 is replaced by the task
        number.

        If the config value is not found, we just return the arg as-is.
        """
        try:
            summary = self.bot.config.wiki["summary"]
        except KeyError:
            return comment
        return summary.replace("$1", str(self.number)).replace("$2", comment)

    def shutoff_enabled(self, site=None):
        """Returns whether on-wiki shutoff is enabled for this task.

        We check a certain page for certain content. This is determined by
        our config file: config.wiki["shutoff"]["page"] is used as the title,
        with $1 replaced by our username and $2 replaced by the task number,
        and config.wiki["shutoff"]["disabled"] is used as the content.

        If the page has that content or the page does not exist, then shutoff
        is "disabled", meaning the bot is supposed to run normally, and we
        return False. If the page's content is something other than what we
        expect, shutoff is enabled, and we return True.

        If a site is not provided, we'll try to use self.site if it's set.
        Otherwise, we'll use our default site.
        """
        if not site:
            try:
                site = self.site
            except AttributeError:
                site = self.bot.wiki.get_site()

        try:
            cfg = self.config.wiki["shutoff"]
        except KeyError:
            return False
        title = cfg.get("page", "User:$1/Shutoff/Task $2")
        username = site.get_user().name()
        title = title.replace("$1", username).replace("$2", str(self.number))
        page = site.get_page(title)

        try:
            content = page.get()
        except wiki.PageNotFoundError:
            return False
        if content == cfg.get("disabled", "run"):
            return False

        self.logger.warn("Emergency task shutoff has been enabled!")
        return True


class TaskManager(object):
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
            builtin_dir = path.dirname(__file__)
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
