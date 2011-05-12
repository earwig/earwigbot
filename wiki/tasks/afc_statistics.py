# -*- coding: utf-8  -*-

# A task to generate statistics for [[WP:AFC]] and save them to [[Template:AFC_statistics]].

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "afc_statistics"
    
    def run(self, **kwargs):
        pass
