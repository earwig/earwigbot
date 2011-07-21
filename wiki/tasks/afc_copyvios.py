# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to check newly-edited [[WP:AFC]] submissions for copyright
    violations."""
    task_name = "afc_copyvios"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
