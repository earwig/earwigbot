# -*- coding: utf-8  -*-

import re

from classes import BaseCommand
import wiki

class Command(BaseCommand):
    """Get information about an AFC submission by name."""
    name = "report"

    def process(self, data):
        self.site = wiki.get_site()
        self.site._maxlag = None
        self.data = data

        if not data.args:
            msg = "what submission do you want me to give information about?"
            self.connection.reply(data, msg)
            return

        title = ' '.join(data.args)
        title = title.replace("http://en.wikipedia.org/wiki/", "")
        title = title.replace("http://enwp.org/", "").strip()

        # Given '!report Foo', first try [[Foo]]:
        if self.report(title):
            return

        # Then try [[Wikipedia:Articles for creation/Foo]]:
        title2 = "".join(("Wikipedia:Articles for creation/", title))
        if self.report(title2):
            return

        # Then try [[Wikipedia talk:Articles for creation/Foo]]:
        title3 = "".join(("Wikipedia talk:Articles for creation/", title))
        if self.report(title3):
            return

        msg = "submission \x0302{0}\x0301 not found.".format(title)
        self.connection.reply(data, msg)

    def report(self, title):
        data = self.data
        page = self.site.get_page(title, follow_redirects=False)
        if not page.exists()[0]:
            return

        url = page.url().replace("en.wikipedia.org/wiki", "enwp.org")
        short = re.sub("wikipedia( talk)?\:articles for creation\/", "", title,
                       flags=re.IGNORECASE)
        status = self.get_status(page)
        user = self.site.get_user(page.creator())
        user_name = user.name()
        user_url = user.get_talkpage().url()

        msg1 = "AfC submission report for \x0302{0}\x0301 ({1}):"
        msg2 = "Status: \x0303{0}\x0301"
        msg3 = "Submitted by \x0302{0}\x0301 ({1})"
        if status == "accepted":
            msg3 = "Reviewed by \x0302{0}\x0301 ({1})"

        self.connection.reply(data, msg1.format(short, url))
        self.connection.say(data.chan, msg2.format(status))
        self.connection.say(data.chan, msg3.format(user_name, user_url))

        return True

    def get_status(self, page):
        content = page.get()

        if page.is_redirect():
            target = page.get_redirect_target()
            if self.site.get_page(target).namespace() == 0:
                return "accepted"
            return "redirect"
        elif re.search("\{\{afc submission\|r\|(.*?)\}\}", content, re.I):
            return "being reviewed"
        elif re.search("\{\{afc submission\|h?\|(.*?)\}\}", content, re.I):
            return "pending"
        elif re.search("\{\{afc submission\|t\|(.*?)\}\}", content, re.I):
            return "unsubmitted draft"
        elif re.search("\{\{afc submission\|d\|(.*?)\}\}", content, re.I):
            regex = "\{\{afc submission\|d\|(.*?)(\||\}\})"
            try:
                reason = re.findall(regex, content, re.I)[0][0]
            except IndexError:
                return "declined"
            return "declined with reason \"{0}\"".format(reason)
        return "unkown"
