# -*- coding: utf-8  -*-

class BaseTask(object):
    """A base class for bot tasks that edit Wikipedia."""
    task_name = None

    def __init__(self):
        """This is called once immediately after the task class is loaded by
        the task manager (in wiki.task_manager.load_class_from_file())."""
        pass

    def run(self, **kwargs):
        """This is called directly by task_manager.start_task() and is the main
        way to make a task do stuff. kwargs will be any keyword arguments
        passed to start_task(), which are (of course) optional. The same task
        instance is preserved between runs, so you can theoretically store data
        in self (e.g. start_task('mytask', action='store', data='foo')) and
        then use it later (e.g. start_task('mytask', action='save'))."""
        pass
