# -*- coding: utf-8  -*-

import re

from classes import BaseCommand
import tasks
import wiki

class Command(BaseCommand):
    """Get information about an AFC submission by name."""
    name = "report"

    def process(self, data):
        self.site = wiki.get_site()
        self.site._maxlag = None
        self.data = data

        try:
            self.statistics = tasks.get("afc_statistics")
        except KeyError:
            e = "Cannot run command: requires afc_statistics task."
            self.logger.error(e)
            return

        if not data.args:
            msg = "what submission do you want me to give information about?"
            self.connection.reply(data, msg)
            return

        title = " ".join(data.args)
        title = title.replace("http://en.wikipedia.org/wiki/", "")
        title = title.replace("http://enwp.org/", "").strip()

        # Given '!report Foo', first try [[Foo]]:
        page = self.get_page(title)
        if page:
            return self.report(page)

        # Then try [[Wikipedia:Articles for creation/Foo]]:
        newtitle = "/".join(("Wikipedia:Articles for creation", title))
        page = self.get_page(newtitle)
        if page:
            return self.report(page)

        # Then try [[Wikipedia talk:Articles for creation/Foo]]:
        newtitle = "/".join(("Wikipedia talk:Articles for creation", title))
        page = self.get_page(newtitle)
        if page:
            return self.report(page)

        msg = "submission \x0302{0}\x0301 not found.".format(title)
        self.connection.reply(data, msg)

    def get_page(self, title):
        page = self.site.get_page(title, follow_redirects=False)
        if page.exists()[0]:
            return page

    def report(self, page):
        url = page.url().replace("en.wikipedia.org/wiki", "enwp.org")
        short = self.statistics.get_short_title(page.title())
        status = self.get_status(page)
        user = self.site.get_user(page.creator())
        user_name = user.name()
        user_url = user.get_talkpage().url()

        msg1 = "AfC submission report for \x0302{0}\x0301 ({1}):"
        msg2 = "Status: \x0303{0}\x0301"
        msg3 = "Submitted by \x0302{0}\x0301 ({1})"
        if status == "accepted":
            msg3 = "Reviewed by \x0302{0}\x0301 ({1})"

        self.connection.reply(self.data, msg1.format(short, url))
        self.connection.say(self.data.chan, msg2.format(status))
        self.connection.say(self.data.chan, msg3.format(user_name, user_url))

    def get_status(self, page):
        if page.is_redirect():
            target = page.get_redirect_target()
            if self.site.get_page(target).namespace() == wiki.NS_MAIN:
                return "accepted"
            return "redirect"

        statuses = self.statistics.get_statuses(page.get())
        if "R" in statuses:
            return "being reviewed"
        elif "H" in statuses:
            return "pending draft"
        elif "P" in statuses:
            return "pending submission"
        elif "T" in statuses:
            return "unsubmitted draft"
        elif "D" in statuses:
            return "declined"
        return "unkown"
