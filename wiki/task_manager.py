# -*- coding: utf-8  -*-

# A module to manage bot tasks.

import time
import traceback
import threading
import os

from config import schedule

task_list = dict() # the key is the task's name, the value is the task's class instance

def load_tasks():
    """Load all valid task classes from wiki/tasks/, and add them to the task_list."""
    files = os.listdir(os.path.join("wiki", "tasks")) # get all files in wiki/tasks/
    files.sort() # alphabetically sort list of files
    for f in files:
        if not os.path.isfile(os.path.join("wiki", "tasks", f)): # ignore non-files
            continue
        if f.startswith("_") or not f.endswith(".py"): # ignore non-python files or files beginning with "_"
            continue
        load_class_from_file(f)
    print "Found %s tasks: %s." % (len(task_list), ', '.join(task_list.keys()))

def load_class_from_file(f):
    """Look in a given file for the task class."""
    global task_list
    
    module = f[:-3] # strip .py from end
    try:
        exec "from wiki.tasks import %s as m" % module
    except: # importing the file failed for some reason...
        print "Couldn't load task file %s:" % f
        traceback.print_exc()
        return
    try:
        task_class = m.Task()
    except:
        print "Couldn't find or get task class in file %s:" % f
        traceback.print_exc()
        return
    task_name = task_class.task_name
    task_list[task_name] = task_class
    print "Added task %s from wiki/tasks/%s..." % (task_name, f)

def start_tasks(now=time.gmtime()):
    """Start all tasks that are supposed to be run at a given time."""
    tasks = schedule.check(now.tm_min, now.tm_hour, now.tm_mday, now.tm_mon, now.tm_wday) # get list of tasks to run this turn
    for task in tasks:
        if isinstance(task, tuple): # they've specified kwargs, so pass those to start_task
            start_task(task[0], **task[1])
        else: # otherwise, just pass task_name
            start_task(task)

def start_task(task_name, **kwargs):
    """Start a given task in a new thread. Pass args to the task's run function."""
    print "Starting task '{}' in a new thread...".format(task_name)
    
    try:
        task = task_list[task_name] # get the class for this task, a subclass of BaseTask
    except KeyError:
        print "Couldn't find task '{}': wiki/tasks/{}.py does not exist.".format(task_name, task_name)
        return
    
    # task_thread = threading.Thread(target=task_wrapper, args=(task, kwargs))
    task_thread = threading.Thread(target=lambda: task_wrapper(task, **kwargs)) # Normally we'd do task_wrapper(task, **kwargs), but because of threading we'd have to do Thread(target=task_wrapper, args=(task, **kwargs)), which doesn't work because the **kwargs is inside a tuple, not inside function params. Use lambda to get around the args=tuple nonsense
    task_thread.name = "task {} (spawned at {} UTC)".format(task_name, time.asctime())
    task_thread.daemon = True # stop bot task threads automagically if the main bot stops
    task_thread.start()

def task_wrapper(task, **kwargs):
    """Wrapper for task classes: run the task and catch any errors."""
    try:
        task.run(**kwargs)
    except:
        print "Task '{}' raised an exception and had to stop:".format(task.task_name)
        traceback.print_exc()
    else:
        print "Task '{}' finished without error.".format(task.task_name)
