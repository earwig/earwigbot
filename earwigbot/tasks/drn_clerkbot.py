# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from os import expanduser
import re

import oursql

from earwigbot.tasks import Task

class DRNClerkBot(Task):
    """A task to clerk for [[WP:DRN]]."""
    name = "drn_clerkbot"
    number = 19

    # Case status:
    STATUS_UNKNOWN = 0
    STATUS_NEW = 1
    STATUS_OPEN = 2
    STATUS_STALE = 3
    STATUS_NEEDASSIST = 4
    STATUS_REVIEW = 5
    STATUS_RESOLVED = 6
    STATUS_CLOSED = 7
    STATUS_ARCHIVE = 8

    def setup(self):
        """Hook called immediately after the task is loaded."""
        cfg = self.config.tasks.get(self.name, {})
        self.title = cfg.get("page", "Wikipedia:Dispute resolution noticeboard")

        # Templates used in chart generation:
        templates = cfg.get("templates", {})
        self.tl_status = templates.get("status", "DR case status")
        self.tl_notify_party = templates.get("notifyParty", "DRN-notice")
        self.tl_notify_stale = templates.get("notifyStale", "DRN stale notice")
        self.tl_archive_top = templates.get("archiveTop", "DRN archive top")
        self.tl_archive_bottom = templates.get("archiveBottom",
                                               "DRN archive bottom")

        # Connection data for our SQL database:
        kwargs = cfg.get("sql", {})
        kwargs["read_default_file"] = expanduser("~/.my.cnf")
        self.conn_data = kwargs
        self.db_access_lock = Lock()

    def run(self, **kwargs):
        """Entry point for a task event."""
        with self.db_access_lock:
            page = self.bot.wiki.get_site().get_page(self.title)
            text = page.get()
            current = read_page(text)

    def read_page(self, text):
        split = re.split("(^==\s*[^=]+?\s*==$)", text, flags=re.M|re.U)
        cases = []
        case = None
        for item in split:
            if item.startswith("=="):
                if case:
                    cases.append(case)
                case = _Case()
                case.title = item[2:-2].strip()
            else:
                templ = re.escape(self.tl_status)
                if case and re.match("\s*\{\{" + templ, item, re.U):
                    case.body = case.old_body = item
                    case.status = self.read_status(body)
        if case:
            cases.append(case)
        return cases

    def read_status(self, body):
        aliases = {
            self.STATUS_NEW: ("",),
            self.STATUS_OPEN: ("open", "active", "inprogress"),
            self.STATUS_STALE: ("stale",),
            self.STATUS_NEEDASSIST: ("needassist", "relist", "relisted"),
            self.STATUS_REVIEW: ("review",),
            self.STATUS_RESOLVED: ("resolved", "resolve"),
            self.STATUS_CLOSED: ("closed", "close"),
        }
        templ = re.escape(self.tl_status)
        status = re.search("\{\{" + templ + "\|?(.*?)\}\}", body, re.S|re.U)
        if not status:
            return self.STATUS_UNKNOWN
        for option, names in aliases.iteritems():
            if status.group(1).lower() in names:
                return option
        return self.STATUS_UNKNOWN


class _Case(object):
    def __init__(self):
        self.title = None
        self.body = None
        self.status = None
