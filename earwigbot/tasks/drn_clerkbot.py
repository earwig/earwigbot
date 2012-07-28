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
from threading import RLock
from time import sleep, time

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

        # Set some wiki-related attributes:
        self.title = cfg.get("page", "Wikipedia:Dispute resolution noticeboard")
        default_summary = "Updating $3 cases for the [[WP:DRN|dispute resolution noticeboard]]."
        self.summary = self.make_summary(cfg.get("summary", default_summary))

        # Templates used:
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
        self.db_access_lock = RLock()

    def run(self, **kwargs):
        """Entry point for a task event."""
        if not self.db_access_lock.acquire(False):  # Non-blocking
            self.logger.info("A job is already ongoing; aborting")
            return

        with self.db_access_lock:
            self.logger.info(u"Starting update to [[{0}]]".format(self.title))
            start = time()
            conn = oursql.connect(**self.conn_data)
            cases = read_database(conn)
            page = self.bot.wiki.get_site().get_page(self.title)
            text = page.get()
            read_page(conn, cases, text)

            # Work!
            # Send messages!

            self.save(page, cases)

    def save(self, page, cases):
        newtext = text = page.get()
        counter = 0
        for case in cases:
            if case.old != case.body:
                newtext = newtext.replace(case.old, case.body)
                counter += 1

        worktime = time() - start
        if worktime < 60:
            sleep(60 - worktime)
        page.reload()
        if page.get() != text:
            log = "Someone has edited the page while we were working; restarting"
            self.logger.warn(log)
            return self.run()
        summary = self.summary.replace("$3", str(counter))
        page.edit(text, summary, minor=False, bot=True)
        self.logger.info(u"Saved page [[{0}]]".format(page.title))

    def read_database(self, conn):
        """Return a list of _Cases from the database."""
        cases = []
        query = "SELECT case_id, case_title, case_status FROM case"
        with conn.cursor() as cursor:
            cursor.execute(query)
            for id_, name, status in cursor:
                cases.append(_Case(id_, title, status))
        return cases

    def read_page(self, conn, cases, text):
        """Read the noticeboard content and update the list of _Cases."""
        tl_status_esc = re.escape(self.tl_status)
        split = re.split("(^==\s*[^=]+?\s*==$)", text, flags=re.M|re.U)
        for i in xrange(len(split)):
            if i + 1 == len(split):
                break
            if not split[i].startswith("=="):
                continue
            title = split[i][2:-2].strip()
            body = old = split[i + 1]
            if not re.search("\s*\{\{" + tl_status_esc, body, re.U):
                continue
            status = self.read_status(body)
            re_id = "<!-- EarwigBot Case ID \(please don't modify me\): (.*?) -->"
            try:
                id_ = re.search(re_id, body).group(1)
                case = [case for case in cases if case.id == id_][0]
            except (AttributeError, IndexError):
                id_ = self.select_next_id(conn)
                re_id2 = "(\{\{" + tl_status_esc + "(.*?)\}\})(<!-- Case ID \(please don't modify\): .*? -->)?"
                repl = ur"\1 <!-- Case ID (please don't modify): {0} -->"
                body = re.sub(re_id2, repl.format(id_), body)
                case = _Case(id_, title, status)
                cases.append(case)
            case.body, case.old = body, old

    def select_next_id(self, conn):
        """Return the next incremental ID for a case."""
        query = "SELECT MAX(case_id) FROM case"
        with conn.cursor() as cursor:
            cursor.execute(query)
            current = cursor.fetchone()[0]
            if current:
                return current + 1
            return 1

    def read_status(self, body):
        """Parse the current status from a case body."""
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
    """A simple object representing a dispute resolution case."""
    def __init__(self, id_, title, status):
        self.id = id_
        self.title = title
        self.status = status

        self.body = None
        self.old = None
