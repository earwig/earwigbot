# -*- coding: utf-8  -*-

from classes import BaseTask

class Task(BaseTask):
    """A task to tag files whose extensions do not agree with their MIME
    type."""
    name = "wrongmime"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
