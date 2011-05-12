# -*- coding: utf-8  -*-

# A task to create daily categories for [[WP:FEED]].

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "feed_dailycats"
    
    def run(self, **kwargs):
        pass
