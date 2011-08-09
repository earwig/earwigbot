# -*- coding: utf-8  -*-

import time

from classes import BaseTask

class Task(BaseTask):
    """A task to generate statistics for [[WP:AFC]] and save them to
    [[Template:AFC_statistics]]."""
    name = "afc_statistics"

    def __init__(self):
        pass

    def run(self, **kwargs):
        time.sleep(5)
        print kwargs
