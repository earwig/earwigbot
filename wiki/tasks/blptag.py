# -*- coding: utf-8  -*-

# A task to add |blp=yes to {{WPB}} or {{WPBS}} when it is used along with {{WP Biography}}.

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "blptag"
    
    def run(self, **kwargs):
        pass
