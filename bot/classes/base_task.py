# -*- coding: utf-8  -*-

class BaseTask(object):
    """A base class for bot tasks that edit Wikipedia."""
    name = None

    def __init__(self):
        """Constructor for new tasks.

        This is called once immediately after the task class is loaded by
        the task manager (in tasks._load_task()).
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
