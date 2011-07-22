# -*- coding: utf-8  -*-

"""
EarwigBot's Wiki Bot Task Manager

This module provides some functions to run and load bot tasks from wiki/tasks/.
"""

import time
import traceback
import threading
import os

from core import config

# store loaded tasks as a dict where the key is the task name and the value is
# an instance of the task class (wiki.tasks.task_file.Task())
task_list = dict()

def load_tasks():
    """Load all valid task classes from wiki/tasks/, and add them to the
    task_list variable."""
    files = os.listdir(os.path.join("wiki", "tasks"))
    files.sort()  # alphabetically sort all files in wiki/tasks/
    for f in files:
        if not os.path.isfile(os.path.join("wiki", "tasks", f)):
            continue  # ignore non-files
        if f.startswith("_") or not f.endswith(".py"):
            continue  # ignore non-python files or files beginning with an _
        load_class_from_file(f)
    print "Found %s tasks: %s." % (len(task_list), ', '.join(task_list.keys()))

def load_class_from_file(f):
    """Look in a given file for the task class."""
    global task_list

    module = f[:-3]  # strip .py from end
    try:
        exec "from wiki.tasks import %s as m" % module
    except:  # importing the file failed for some reason...
        print "Couldn't load task file %s:" % f
        traceback.print_exc()
        return
    try:
        task_class = m.Task
    except:
        print "Couldn't find or get task class in file %s:" % f
        traceback.print_exc()
        return
    task_name = task_class.task_name
    task_list[task_name] = task_class()
    print "Added task %s from wiki/tasks/%s..." % (task_name, f)

def start_tasks(now=time.gmtime()):
    """Start all tasks that are supposed to be run at a given time."""
    tasks = config.schedule(now.tm_min, now.tm_hour, now.tm_mday, now.tm_mon,
            now.tm_wday)  # get list of tasks to run this turn

    for task in tasks:
        if isinstance(task, list):          # they've specified kwargs
            start_task(task[0], **task[1])  # so pass those to start_task
        else:  # otherwise, just pass task_name
            start_task(task)

def start_task(task_name, **kwargs):
    """Start a given task in a new thread. Pass args to the task's run()
    function."""
    print "Starting task '{0}' in a new thread...".format(task_name)

    try:
        task = task_list[task_name]
    except KeyError:
        print ("Couldn't find task '{0}': wiki/tasks/{0}.py does not exist.").format(task_name)
        return

    task_thread = threading.Thread(target=lambda: task_wrapper(task, **kwargs))
    task_thread.name = "{0} ({1})".format(task_name, time.strftime("%b %d %H:%M:%S"))

    # stop bot task threads automagically if the main bot stops
    task_thread.daemon = True

    task_thread.start()

def task_wrapper(task, **kwargs):
    """Wrapper for task classes: run the task and catch any errors."""
    try:
        task.run(**kwargs)
    except:
        print "Task '{0}' raised an exception and had to stop:".format(task.task_name)
        traceback.print_exc()
    else:
        print "Task '{0}' finished without error.".format(task.task_name)
