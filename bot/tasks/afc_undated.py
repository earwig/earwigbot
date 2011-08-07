# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to clear [[Category:Undated AfC submissions]]."""
    task_name = "afc_undated"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
