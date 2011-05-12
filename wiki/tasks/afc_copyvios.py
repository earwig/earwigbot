# -*- coding: utf-8  -*-

# A task to check newly-edited [[WP:AFC]] submissions for copyright violations.

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "afc_copyvios"
    
    def run(self, **kwargs):
        pass
