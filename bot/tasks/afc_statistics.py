# -*- coding: utf-8  -*-

import re
from os import path

from classes import BaseTask
import config
import wiki

class Task(BaseTask):
    """A task to generate statistics for WikiProject Articles for Creation.

    Statistics are stored in the file indicated by self.filename,
    "statistics.txt" in the bot's root directory being the default. They are
    updated live while watching the recent changes IRC feed.

    The bot saves its statistics once an hour, on the hour, to self.pagename.
    In the live bot, this is "Template:AFC statistics".
    """
    name = "afc_statistics"
    number = 2

    def __init__(self):
        self.filename = path.join(config.root_dir, "statistics.txt")
        self.cfg = config.tasks.get(self.name, {})
        self.pagename = cfg.get("page", "Template:AFC statistics")
        default = "Updating statistics for [[WP:WPAFC|WikiProject Articles for creation]]."
        self.summary = self.make_summary(cfg.get("summary", default))

    def run(self, **kwargs):
        self.site = wiki.get_site()
        
        action = kwargs.get("action")
        if not action:
            return
        if action == "save":
            self.save()
            return

        page = kwargs.get("page")
        if page:
            methods = {
                "edit": self.process_edit,
                "move": self.process_move,
                "delete": self.process_delete,
                "restore": self.process_restore,
            }
            method = methods.get(action)
            if method:
                method(page)

    def save(self):
        if self.shutoff_enabled():
            return
        try:
            with open(self.filename) as fp:
                statistics = fp.read()
        except IOError:
            pass

        page = self.site.get_page(self.pagename)
        text = page.get()
        newtext = re.sub("(<!-- stat begin -->)(.*?)(<!-- stat end -->)",
                         "\\1~~~~\\3", text, flags=re.DOTALL)
        if newtext == text:
            return  # Don't edit the page if we're not adding anything

        newtext = re.sub("(<!-- sig begin -->)(.*?)(<!-- sig end -->)",
                         "\\1~~~~\\3", newtext)
        page.edit(newtext, self.summary, minor=True)

    def process_edit(self, page):
        pass

    def process_move(self, page):
        pass

    def process_delete(self, page):
        pass

    def process_restore(self, page):
        pass
