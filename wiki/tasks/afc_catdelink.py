# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to delink mainspace categories in declined [[WP:AFC]]
    submissions."""
    task_name = "afc_catdelink"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
