# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Task Manager

This package provides the wiki bot "tasks" EarwigBot runs. Here in __init__,
you can find some functions used to load and run these tasks.
"""

import os
import sys
import threading
import time
import traceback

from classes import BaseTask
import config

__all__ = ["load", "schedule", "start", "get_all"]

# Base directory when searching for tasks:
base_dir = os.path.join(config.root_dir, "bot", "tasks")

# Store loaded tasks as a dict where the key is the task name and the value is
# an instance of the task class:
_tasks = {}

def _load_task(filename):
    """Try to load a specific task from a module, identified by file name."""
    global _tasks

    # Strip .py from the end of the filename and join with our package name:
    name = ".".join(("tasks", filename[:-3]))
    try:
         __import__(name)
    except:
        print "Couldn't load file {0}:".format(filename)
        traceback.print_exc()
        return

    task = sys.modules[name].Task()
    if not isinstance(task, BaseTask):
        return

    _tasks[task.name] = task
    print "Added task {0}...".format(task.name)

def _wrapper(task, **kwargs):
    """Wrapper for task classes: run the task and catch any errors."""
    try:
        task.run(**kwargs)
    except:
        error = "Task '{0}' raised an exception and had to stop:"
        print error.format(task.name)
        traceback.print_exc()
    else:
        print "Task '{0}' finished without error.".format(task.name)

def load():
    """Load all valid tasks from bot/tasks/, into the _tasks variable."""
    files = os.listdir(base_dir)
    files.sort()

    for filename in files:
        if filename.startswith("_") or not filename.endswith(".py"):
            continue
        try:
            _load_task(filename)
        except AttributeError:
            pass  # The file is doesn't contain a task, so just move on

    print "Found {0} tasks: {1}.".format(len(_tasks), ', '.join(_tasks.keys()))

def schedule(now=time.gmtime()):
    """Start all tasks that are supposed to be run at a given time."""
    # Get list of tasks to run this turn:
    tasks = config.schedule(now.tm_min, now.tm_hour, now.tm_mday, now.tm_mon,
                            now.tm_wday) 

    for task in tasks:
        if isinstance(task, list):     # they've specified kwargs
            start(task[0], **task[1])  # so pass those to start_task
        else:  # otherwise, just pass task_name
            start(task)

def start(task_name, **kwargs):
    """Start a given task in a new thread. Pass args to the task's run()
    function."""
    print "Starting task '{0}' in a new thread...".format(task_name)

    try:
        task = _tasks[task_name]
    except KeyError:
        error = "Couldn't find task '{0}': bot/tasks/{0}.py does not exist."
        print error.format(task_name)
        return

    task_thread = threading.Thread(target=lambda: _wrapper(task, **kwargs))
    start_time = time.strftime("%b %d %H:%M:%S")
    task_thread.name = "{0} ({1})".format(task_name, start_time)

    # Stop bot task threads automagically if the main bot stops:
    task_thread.daemon = True

    task_thread.start()

def get_all():
    """Return our dict of all loaded tasks."""
    return _tasks
