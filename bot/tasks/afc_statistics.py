# -*- coding: utf-8  -*-

from os import path

from classes import BaseTask
import config

class Task(BaseTask):
    """A task to generate statistics for WikiProject Articles for Creation.

    Statistics are stored in the file indicated by self.filename,
    "statistics.txt" in the bot's root directory being the default. They are
    updated live while watching the recent changes IRC feed.

    The bot saves its statistics once an hour, on the hour, to self.pagename.
    In the live bot, this is "Template:AFC statistics".
    """
    name = "afc_statistics"

    def __init__(self):
        self.filename = path.join(config.root_dir, "statistics.txt")
        self.pagename = "User:EarwigBot/Sandbox/Statistics"

    def run(self, **kwargs):
        try:
            action = kwargs["action"]
        except KeyError:
            return

        if action == "save":
            self.save()
        else:
            try:
                page = kwargs["page"]
            except KeyError:
                return
            if action == "edit":
                self.process_edit(page)
            elif action == "move":
                self.process_move(page)
            elif action == "delete":
                self.process_delete(page)
            elif action == "restore":
                self.process_restore(page)

    def save(self):
        pass

    def process_edit(self, page):
        pass

    def process_move(self, page):
        pass

    def process_delete(self, page):
        pass

    def process_restore(self, page):
        pass
