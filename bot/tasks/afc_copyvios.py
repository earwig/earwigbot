# -*- coding: utf-8  -*-

from classes import BaseTask

class Task(BaseTask):
    """A task to check newly-edited [[WP:AFC]] submissions for copyright
    violations."""
    name = "afc_copyvios"
    number = 1

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
