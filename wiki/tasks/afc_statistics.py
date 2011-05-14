# -*- coding: utf-8  -*-

# A task to generate statistics for [[WP:AFC]] and save them to [[Template:AFC_statistics]].

import time

from wiki.base_task import BaseTask

class Task(BaseTask):
    def __init__(self):
        self.task_name = "afc_statistics"
    
    def run(self, **kwargs):
        time.sleep(10)
        print "kwargs: {}".format(kwargs)
