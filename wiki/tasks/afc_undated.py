# -*- coding: utf-8  -*-

# A task to clear [[Category:Undated AfC submissions]].

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "afc_undated"
    
    def run(self, **kwargs):
        pass
