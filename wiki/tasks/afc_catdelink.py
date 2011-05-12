# -*- coding: utf-8  -*-

# A task to delink mainspace categories in declined [[WP:AFC]] submissions.

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "afc_catdelink"
    
    def run(self, **kwargs):
        pass
