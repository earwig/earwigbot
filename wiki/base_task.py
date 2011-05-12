# -*- coding: utf-8  -*-

# A base class for bot tasks that edit Wikipedia.

class BaseTask(object):
    def __init__(self):
        """A base class for bot tasks that edit Wikipedia."""
        self.task_name = None

    def run(self, **kwargs):
        """Run this task."""
        pass
