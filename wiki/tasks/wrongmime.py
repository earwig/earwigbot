# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to tag files whose extensions do not agree with their MIME
    type."""
    task_name = "wrongmime"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
