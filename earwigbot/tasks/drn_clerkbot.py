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

from datetime import datetime
from os import expanduser
import re
from threading import RLock
from time import sleep, time

import oursql

from earwigbot import exceptions
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

    ALIASES = {
        STATUS_NEW: ("",),
        STATUS_OPEN: ("open", "active", "inprogress"),
        STATUS_STALE: ("stale",),
        STATUS_NEEDASSIST: ("needassist", "relist", "relisted"),
        STATUS_REVIEW: ("review",),
        STATUS_RESOLVED: ("resolved", "resolve"),
        STATUS_CLOSED: ("closed", "close"),
    }

    def setup(self):
        """Hook called immediately after the task is loaded."""
        cfg = self.config.tasks.get(self.name, {})

        # Set some wiki-related attributes:
        self.title = cfg.get("title", "Wikipedia:Dispute resolution noticeboard")
        self.talk = cfg.get("talk", "Wikipedia talk:Dispute resolution noticeboard")
        self.volunteer_title = cfg.get("volunteers", "Wikipedia:Dispute resolution noticeboard/Volunteering")
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
        action = kwargs.get("action", "all")
        try:
            start = time()
            conn = oursql.connect(**self.conn_data)
            site = self.bot.wiki.get_site()
            if action in ["all", "update_volunteers"]:
                self.update_volunteers(conn, site)
            if action in ["all", "clerk"]:
                log = u"Starting update to [[{0}]]".format(self.title)
                self.logger.info(log)
                cases = self.read_database(conn)
                page = site.get_page(self.title)
                text = page.get()
                self.read_page(conn, cases, text)
                noticies = self.clerk(conn, cases)
                self.save(page, cases, kwargs)
                self.send_notices(site, notices)
        finally:
            self.db_access_lock.release()

    def update_volunteers(self, conn, site):
        """Updates and stores the list of dispute resolution volunteers."""
        log = u"Updating volunteer list from [[{0}]]"
        self.logger.info(log.format(self.volunteer_title))
        page = site.get_page(self.volunteer_title)
        try:
            text = page.get()
        except exceptions.PageNotFoundError:
            text = ""
        marker = "<!-- please don't remove this comment (used by EarwigBot) -->"
        if marker not in text:
            log = u"The marker ({0}) wasn't found in the volunteer list at [[{1}]]!"
            self.logger.error(log.format(marker, page.title))
        text = text.split(marker)[1]
        additions = set()
        for line in text.splitlines():
            user = re.search("\# \{\{User\|(.*?)\}\}", line)
            if user:
                additions.add((user.group(1)))

        removals = set()
        query1 = "SELECT volunteer_username FROM volunteer"
        query2 = "DELETE FROM volunteer WHERE volunteer_username = ?"
        query3 = "INSERT INTO volunteer VALUES (?)"
        with conn.cursor() as cursor:
            cursor.execute(query1)
            for row in cursor:
                if row in additions:
                    additions.remove(row)
                else:
                    removals.add(row)
            if removals:
                cursor.executemany(query2, removals)
            if additions:
                cursor.executemany(query3, additions)

    def read_database(self, conn):
        """Return a list of _Cases from the database."""
        cases = []
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM case")
            for row in cursor:
                case = _Case(*row, new=False)
                cases.append(case)
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
            re_id = "<!-- Bot Case ID \(please don't modify\): (.*?) -->"
            try:
                id_ = re.search(re_id, body).group(1)
                case = [case for case in cases if case.id == id_][0]
            except (AttributeError, IndexError):
                id_ = self.select_next_id(conn, "case_id", "case")
                re_id2 = "(\{\{" + tl_status_esc
                re_id2 += "(.*?)\}\})(<!-- Bot Case ID \(please don't modify\): .*? -->)?"
                repl = ur"\1 <!-- Bot Case ID (please don't modify): {0} -->"
                body = re.sub(re_id2, repl.format(id_), body)
                case = _Case(id_, title, status, self.STATUS_UNKNOWN, time(),
                             0, False, False, new=True)
                cases.append(case)
            else:
                case.status = status
                if case.title != title:
                    self.update_case_title(conn, id_, title)
                    case.title = title
            case.body, case.old = body, old

    def select_next_id(self, conn, column, table):
        """Return the next incremental ID for a case."""
        query = "SELECT MAX(?) FROM ?"
        with conn.cursor() as cursor:
            cursor.execute(query, (column, table))
            current = cursor.fetchone()[0]
            if current:
                return current + 1
            return 1

    def read_status(self, body):
        """Parse the current status from a case body."""
        templ = re.escape(self.tl_status)
        status = re.search("\{\{" + templ + "\|?(.*?)\}\}", body, re.S|re.U)
        if not status:
            return self.STATUS_UNKNOWN
        for option, names in self.ALIASES.iteritems():
            if status.group(1).lower() in names:
                return option
        return self.STATUS_UNKNOWN

    def update_case_title(self, conn, id_, title):
        """Update a case title in the database."""
        query = "UPDATE case SET case_title = ? WHERE case_id = ?"
        with conn.cursor() as cursor:
            cursor.execute(query, (title, id_))

    def clerk(self, conn, cases):
        """Actually go through cases and modify those to be updated."""
        query = "SELECT volunteer_username FROM volunteer"
        with conn.cursor() as cursor:
            cursor.execute(query)
            volunteers = [name for (name,) in cursor.fetchall()]
        notices = []
        for case in cases:
            notices += self.clerk_case(conn, case, volunteers)
        return notices

    def clerk_case(self, conn, case, volunteers):
        """Clerk a particular case and return a list of any notices to send."""
        notices = []
        signatures = self.read_signatures(case.body)
        storedsigs = self.get_signatures_from_db(conn, case)
        if case.status == self.STATUS_NEW:
            notices = self.clerk_new_case(case, volunteers, signatures)
        elif case.status == self.STATUS_OPEN:
            notices = self.clerk_open_case(case, signatures)
        elif case.status == self.STATUS_NEEDASSIST:
            notices = self.clerk_needassist_case(case, volunteers, signatures,
                                                 storedsigs)
        elif case.status == self.STATUS_STALE:
            notices = self.clerk_stale_case(case, signatures, storedsigs)
        elif case.status == self.STATUS_REVIEW:
            notices = self.clerk_review_case(case)
        elif case.status in [self.STATUS_RESOLVED, self.STATUS_CLOSED]:
            self.clerk_closed_case(conn, signatures)
        else:
            log = u"Unsure of how to deal with case {0} (title: {1})"
            self.logger.error(log.format(case.id, case.title))
            return notices
        self.save_case_updates(conn, case, signatures, storedsigs)
        return notices

    def clerk_new_case(self, case, volunteers, signatures):
        notices = self.notify_parties(case)
        if any([editor in volunteers for (editor, timestamp) in signatures]):
            if case.last_action != self.STATUS_OPEN:
                case.status = self.STATUS_OPEN
        return notices

    def clerk_open_case(self, case, signatures):
        flagged = self.check_for_review(case):
        if flagged:
            return flagged

        if len(case.body) - SIZE_WHEN_LAST_VOLUNTEER_EDIT > 15000:                  # TODO
            if case.last_action != self.STATUS_NEEDASSIST:
                case.status = self.STATUS_NEEDASSIST
                return self.build_talk_notice(self.STATUS_NEEDASSIST)

        timestamps = [timestamp for (editor, timestamp) in signatures]
        if time() - max(timestamps) > 60 * 60 * 24 * 2:
            if case.last_action != self.STATUS_STALE:
                case.status = self.STATUS_STALE
                return self.build_talk_notice(self.STATUS_STALE)
        return []

    def clerk_needassist_case(self, case, volunteers, signatures, storedsigs):
        flagged = self.check_for_review(case):
        if flagged:
            return flagged

        newsigs = set(signatures) - set(storedsigs)
        if any([editor in volunteers for (editor, timestamp) in newsigs]):
            if case.last_action != self.STATUS_OPEN:
                case.status = self.STATUS_OPEN
        return []

    def clerk_stale_case(self, case, signatures, storedsigs):
        flagged = self.check_for_review(case):
        if flagged:
            return flagged

        if set(signatures) - set(storedsigs)
            if case.last_action != self.STATUS_OPEN:
                case.status = self.STATUS_OPEN
        return []

    def clerk_review_case(self, case):
        if time() - case.file_time > 60 * 60 * 24 * 7:
            if not case.very_old_notified:
                case.very_old_notified = True
                return SEND_MESSAGE_TO_ZHANG                                        # TODO
        return []

    def clerk_closed_case(self, case, signatures):
        if not case.close_time:
            case.close_time = time()
        timestamps = [timestamp for (editor, timestamp) in signatures]
        closed_long_ago = time() - case.close_time > 60 * 60 * 24
        modified_long_ago = time() - max(timestamps) > 60 * 60 * 24
        if closed_long_ago and modified_long_ago:
            case.status = self.STATUS_ARCHIVE
            case.body = "{{" + self.tl_archive_top + "}}\n" + case.body
            case.body += "\n{{" + self.tl_archive_bottom + "}}"
            reg = "<!-- \[\[User:DoNotArchiveUntil\]\] .*? -->(<!-- .*? -->)?"
            case.body = re.sub(reg, "", case.body)

    def check_for_review(self, case):
        if time() - case.file_time > 60 * 60 * 24 * 4:
            if case.last_action != self.STATUS_REVIEW:
                case.status = self.STATUS_REVIEW
                return self.build_talk_notice(self.STATUS_REVIEW)

    def read_signatures(self, text):
        raise NotImplementedError()                                                 # TODO
        return [(username, timestamp_datetime)...]

    def get_signatures_from_db(self, conn, case):
        query = "SELECT signature_username, signature_timestamp FROM signature WHERE signature_case = ?"
        with conn.cursor() as cursor:
            cursor.execute(query, (case.id,))
            return cursor.fetchall()

    def build_talk_notice(self, status):
        param = self.ALIASES[status][0]
        template = "{{subst:" + self.tl_notify_stale + "|" + param + "}} ~~~~"
        return _Notice(self.talk, template)

    def notify_parties(self, case):
        if case.parties_notified:
            return
        raise NotImplementedError()                                                 # TODO
        case.parties_notified = True

    def save_case_updates(self, conn, case, signatures, storedsigs):
        if case.status != case.original_status:
            case.last_action = case.status
            new = self.ALIASES[case.status][0]
            tl_status_esc = re.escape(self.tl_status)
            search = "\{\{" + tl_status_esc + "(\|?.*?)\}\}"
            repl = "{{" + self.tl_status + "|" + new + "}}"
            case.body = re.sub(search, repl, case.body)

        if case.new:
            self.save_new_case(conn, case)
        else:
            self.save_existing_case(conn, case)

        with conn.cursor() as cursor:
            query1 = "DELETE FROM signature WHERE signature_case = ? AND signature_username = ? AND signature_timestamp = ?"
            query2 = "INSERT INTO signature VALUES (?, ?, ?, ?)"
            removals = set(storedsigs) - set(signatures)
            additions = set(signatures) - set(storedsigs)
            if removals:
                args = [(case.id, name, stamp) for (name, stamp) in removals]
                cursor.execute(query1, args)
            if additions:
                nextid = self.select_next_id(conn, "signature_id", "signature")
                args = []
                for name, stamp in additions:
                    args.append((nextid, case.id, name, stamp))
                    nextid += 1
                cursor.execute(query2, args)

    def save_new_case(self, conn, case):
        args = (case.id, case.title, case.status, case.last_action,
                case.file_time, case.close_time, case.parties_notified,
                case.very_old_notified)
        with conn.cursor() as cursor:
            query = "INSERT INTO case VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, args)

    def save_existing_case(self, conn, case):
        with conn.cursor(oursql.DictCursor) as cursor:
            query = "SELECT * FROM case WHERE case_id = ?"
            cursor.execute(query, (case.id,))
            stored = cursor.fetchone()

        with conn.cursor() as cursor:
            changes, args = [], []
            fields_to_check = [
                ("case_status", case.status),
                ("case_last_action", case.last_action),
                ("case_close_time", case.close_time),
                ("case_parties_notified", case.parties_notified),
                ("case_very_old_notified", case.very_old_notified)
            ]
            for column, data in fields_to_check:
                if data != stored[column]:
                    changes.append(column + " = ?")
                    args.append(data)
            if changes:
                changes = ", ".join(changes)
                args.append(case.id)
                query = "UPDATE case SET {0} WHERE case_id = ?".format(changes)
                cursor.execute(query, args)

    def save(self, page, cases, kwargs):
        """Save any changes to the noticeboard."""
        newtext = text = page.get()
        counter = 0
        for case in cases:
            if case.old != case.body:
                newtext = newtext.replace(case.old, case.body)
                counter += 1
        if newtext == text:
            self.logger.info(u"Nothing to edit on [[{0}]]".format(page.title))
            return

        worktime = time() - start
        if worktime < 60:
            sleep(60 - worktime)
        page.reload()
        if page.get() != text:
            log = "Someone has edited the page while we were working; restarting"
            self.logger.warn(log)
            return self.run(**kwargs)
        summary = self.summary.replace("$3", str(counter))
        page.edit(text, summary, minor=True, bot=True)
        self.logger.info(u"Saved page [[{0}]]".format(page.title))

    def send_notices(self, site, notices):
        """Send out any templated notices to users or pages."""
        if not notices:
            self.logger.info("No notices to send; finishing")
            return
        for notice in notices:
            target, template = notice.target, notice.template
            log = u"Notifying [[{0}]] with {1}".format(target, template)
            self.logger.info(log)
            page = site.get_page(target)
            try:
                text = page.get()
            except exceptions.PageNotFoundError:
                text = ""
            if notice.too_late and notice.too_late in text:
                log = u"Skipping [[{0}]]; was already notified".format(target)
                self.logger.info(log)
            text += ("\n" if text else "") + template
            try:
                page.edit(text, summary, minor=False, bot=True)
            except exceptions.EditError as error:
                name, msg = type(error).name, error.message
                log = u"Couldn't leave notice on {0} because of {1}: {2}"
                self.logger.error(log.format(page.title, name, msg))

        self.logger.info("Done sending notices")


class _Case(object):
    """A object representing a dispute resolution case."""
    def __init__(self, id_, title, status, last_action, file_time, close_time,
                 parties_notified, very_old_notified, new):
        self.id = id_
        self.title = title
        self.status = status
        self.last_action = last_action
        self.file_time = file_time
        self.close_time = close_time
        self.parties_notified = parties_notified
        self.very_old_notified = very_old_notified
        self.new = new

        self.original_status = status
        self.body = None
        self.old = None


class _Notice(object):
    """An object representing a notice to be sent to a user or a page."""
    def __init__(self, target, template, too_late=None):
        self.target = target
        self.template = template
        self.too_late = too_late
