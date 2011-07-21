# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to generate statistics for [[WP:AFC]] and save them to
    [[Template:AFC_statistics]]."""
    task_name = "afc_statistics"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
