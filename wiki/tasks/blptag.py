# -*- coding: utf-8  -*-

from wiki.base_task import BaseTask

class Task(BaseTask):
    """A task to add |blp=yes to {{WPB}} or {{WPBS}} when it is used along with
    {{WP Biography}}."""
    task_name = "blptag"

    def __init__(self):
        pass

    def run(self, **kwargs):
        pass
