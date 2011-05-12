# -*- coding: utf-8  -*-

# A task to tag files whose extensions do not agree with their MIME type.

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "wrongmime"
    
    def run(self, **kwargs):
        pass
