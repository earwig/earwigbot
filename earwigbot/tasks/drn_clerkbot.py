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
from os.path import expanduser
import re
from threading import RLock
from time import mktime, sleep, time

import oursql

from earwigbot import exceptions
from earwigbot.tasks import Task
from earwigbot.wiki import constants

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
        self.title = cfg.get("title",
                             "Wikipedia:Dispute resolution noticeboard")
        self.chart_title = cfg.get("chartTitle", "Template:DRN case status")
        self.volunteer_title = cfg.get("volunteers",
                                       "Wikipedia:Dispute resolution noticeboard/Volunteering")
        self.very_old_title = cfg.get("veryOldTitle", "User talk:Szhang (WMF)")

        clerk_summary = "Updating $3 case$4."
        notify_summary = "Notifying user regarding [[WP:DRN|dispute resolution noticeboard]] case."
        chart_summary = "Updating statistics for the [[WP:DRN|dispute resolution noticeboard]]."
        self.clerk_summary = self.make_summary(cfg.get("clerkSummary", clerk_summary))
        self.notify_summary = self.make_summary(cfg.get("notifySummary", notify_summary))
        self.chart_summary = self.make_summary(cfg.get("chartSummary", chart_summary))

        # Templates used:
        templates = cfg.get("templates", {})
        self.tl_status = templates.get("status", "DR case status")
        self.tl_notify_party = templates.get("notifyParty", "DRN-notice")
        self.tl_notify_stale = templates.get("notifyStale", "DRN stale notice")
        self.tl_archive_top = templates.get("archiveTop", "DRN archive top")
        self.tl_archive_bottom = templates.get("archiveBottom",
                                               "DRN archive bottom")
        self.tl_chart_header = templates.get("chartHeader",
                                             "DRN case status/header")
        self.tl_chart_row = templates.get("chartRow", "DRN case status/row")
        self.tl_chart_footer = templates.get("chartFooter",
                                             "DRN case status/footer")

        # Connection data for our SQL database:
        kwargs = cfg.get("sql", {})
        kwargs["read_default_file"] = expanduser("~/.my.cnf")
        self.conn_data = kwargs
        self.db_access_lock = RLock()

        # Minimum size a MySQL TIMESTAMP field can hold:
        self.min_ts = datetime(1970, 1, 1, 0, 0, 1)

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
                notices = self.clerk(conn, cases)
                if self.shutoff_enabled():
                    return
                if not self.save(page, cases, kwargs, start):
                    return
                self.send_notices(site, notices)
            if action in ["all", "update_chart"]:
                if self.shutoff_enabled():
                    return
                self.update_chart(conn, site)
            if action in ["all", "purge"]:
                self.purge_old_data(conn)
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
            return
        text = text.split(marker)[1]
        additions = set()
        for line in text.splitlines():
            user = re.search("\# \{\{User\|(.+?)\}\}", line)
            if user:
                uname = user.group(1).replace("_", " ").strip()
                additions.add((uname[0].upper() + uname[1:],))

        removals = set()
        query1 = "SELECT volunteer_username FROM volunteers"
        query2 = "DELETE FROM volunteers WHERE volunteer_username = ?"
        query3 = "INSERT INTO volunteers (volunteer_username) VALUES (?)"
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
        query = "SELECT * FROM cases"
        with conn.cursor() as cursor:
            cursor.execute(query)
            for row in cursor:
                case = _Case(*row)
                cases.append(case)
        log = "Read {0} cases from the database"
        self.logger.debug(log.format(len(cases)))
        return cases

    def read_page(self, conn, cases, text):
        """Read the noticeboard content and update the list of _Cases."""
        nextid = self.select_next_id(conn)
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
                id_ = int(re.search(re_id, body).group(1))
                case = [case for case in cases if case.id == id_][0]
            except (AttributeError, IndexError, ValueError):
                id_ = nextid
                nextid += 1
                re_id2 = "(\{\{" + tl_status_esc
                re_id2 += r"(.*?)\}\})(<!-- Bot Case ID \(please don't modify\): .*? -->)?"
                repl = ur"\1 <!-- Bot Case ID (please don't modify): {0} -->"
                body = re.sub(re_id2, repl.format(id_), body)
                re_f = r"\{\{drn filing editor\|(.*?)\|"
                re_f += r"(\d{2}:\d{2},\s\d{1,2}\s\w+\s\d{4}\s\(UTC\))\}\}"
                match = re.search(re_f, body, re.U)
                if match:
                    f_user = match.group(1).split("/", 1)[0].replace("_", " ")
                    f_user = f_user[0].upper() + f_user[1:]
                    strp = "%H:%M, %d %B %Y (UTC)"
                    f_time = datetime.strptime(match.group(2), strp)
                else:
                    f_user, f_time = None, datetime.utcnow()
                case = _Case(id_, title, status, self.STATUS_UNKNOWN, f_user,
                             f_time, f_user, f_time, "", self.min_ts,
                             self.min_ts, False, False, False, len(body),
                             new=True)
                cases.append(case)
                log = u"Added new case {0} ('{1}', status={2}, by {3})"
                self.logger.debug(log.format(id_, title, status, f_user))
            else:
                case.status = status
                log = u"Read active case {0} ('{1}')".format(id_, title)
                self.logger.debug(log)
                if case.title != title:
                    self.update_case_title(conn, id_, title)
                    case.title = title
            case.body, case.old = body, old

        for case in cases[:]:
            if case.body is None:
                if case.original_status == self.STATUS_UNKNOWN:
                    cases.remove(case)  # Ignore archived case
                else:
                    case.status = self.STATUS_UNKNOWN
                    log = u"Dropped case {0} because it is no longer on the page ('{1}')"
                    self.logger.debug(log.format(case.id, case.title))

        self.logger.debug("Done reading cases from the noticeboard page")

    def select_next_id(self, conn):
        """Return the next incremental ID for a case."""
        query = "SELECT MAX(case_id) FROM cases"
        with conn.cursor() as cursor:
            cursor.execute(query)
            current = cursor.fetchone()[0]
            if current:
                return int(current) + 1
            return 1

    def read_status(self, body):
        """Parse the current status from a case body."""
        templ = re.escape(self.tl_status)
        status = re.search("\{\{" + templ + "\|?(.*?)\}\}", body, re.S|re.U)
        if not status:
            return self.STATUS_NEW
        for option, names in self.ALIASES.iteritems():
            if status.group(1).lower() in names:
                return option
        return self.STATUS_NEW

    def update_case_title(self, conn, id_, title):
        """Update a case title in the database."""
        query = "UPDATE cases SET case_title = ? WHERE case_id = ?"
        with conn.cursor() as cursor:
            cursor.execute(query, (title, id_))
        log = u"Updated title of case {0} to '{1}'".format(id_, title)
        self.logger.debug(log)

    def clerk(self, conn, cases):
        """Actually go through cases and modify those to be updated."""
        query = "SELECT volunteer_username FROM volunteers"
        with conn.cursor() as cursor:
            cursor.execute(query)
            volunteers = [name for (name,) in cursor.fetchall()]
        notices = []
        for case in cases:
            log = u"Clerking case {0} ('{1}')".format(case.id, case.title)
            self.logger.debug(log)
            if case.status == self.STATUS_UNKNOWN:
                self.save_existing_case(conn, case)
            else:
                notices += self.clerk_case(conn, case, volunteers)
        self.logger.debug("Done clerking cases")
        return notices

    def clerk_case(self, conn, case, volunteers):
        """Clerk a particular case and return a list of any notices to send."""
        notices = []
        signatures = self.read_signatures(case.body)
        storedsigs = self.get_signatures_from_db(conn, case)
        newsigs = set(signatures) - set(storedsigs)
        if any([editor in volunteers for (editor, timestamp) in newsigs]):
            case.last_volunteer_size = len(case.body)

        if case.status == self.STATUS_NEW:
            notices = self.clerk_new_case(case, volunteers, signatures)
        elif case.status == self.STATUS_OPEN:
            notices = self.clerk_open_case(case, signatures)
        elif case.status == self.STATUS_NEEDASSIST:
            notices = self.clerk_needassist_case(case, volunteers, newsigs)
        elif case.status == self.STATUS_STALE:
            notices = self.clerk_stale_case(case, newsigs)
        elif case.status == self.STATUS_REVIEW:
            notices = self.clerk_review_case(case)
        elif case.status in [self.STATUS_RESOLVED, self.STATUS_CLOSED]:
            self.clerk_closed_case(case, signatures)
        self.save_case_updates(conn, case, volunteers, signatures, storedsigs)
        return notices

    def clerk_new_case(self, case, volunteers, signatures):
        """Clerk a case in the "brand new" state.

        The case will be set to "open" if a volunteer edits it, or "needassist"
        if it increases by over 15,000 bytes or goes by without any volunteer
        edits for two days.
        """
        notices = self.notify_parties(case)
        if any([editor in volunteers for (editor, timestamp) in signatures]):
            self.update_status(case, self.STATUS_OPEN)
        else:
            age = (datetime.utcnow() - case.file_time).total_seconds()
            if age > 60 * 60 * 24 * 2:
                self.update_status(case, self.STATUS_NEEDASSIST)
            elif len(case.body) - case.last_volunteer_size > 15000:
                self.update_status(case, self.STATUS_NEEDASSIST)
        return notices

    def clerk_open_case(self, case, signatures):
        """Clerk an open case (has been edited by a reviewer).

        The case will be set to "needassist" if 15,000 bytes have been added
        since a volunteer last edited, "stale" if no edits have occured in two
        days, or "review" if it has been open for over four days.
        """
        if self.check_for_review(case):
            return []
        if len(case.body) - case.last_volunteer_size > 15000:
            self.update_status(case, self.STATUS_NEEDASSIST)
        timestamps = [timestamp for (editor, timestamp) in signatures]
        if timestamps:
            age = (datetime.utcnow() - max(timestamps)).total_seconds()
            if age > 60 * 60 * 24 * 2:
                self.update_status(case, self.STATUS_STALE)
        return []

    def clerk_needassist_case(self, case, volunteers, newsigs):
        """Clerk a "needassist" case (no volunteer edits in 15,000 bytes).

        The case will be set to "open" if a volunteer edits, or "review" if it
        has been open for over four days.
        """
        if self.check_for_review(case):
            return []
        if any([editor in volunteers for (editor, timestamp) in newsigs]):
            self.update_status(case, self.STATUS_OPEN)
        return []

    def clerk_stale_case(self, case, newsigs):
        """Clerk a stale case (no edits in two days).

        The case will be set to "open" if anyone edits, or "review" if it has
        been open for over four days.
        """
        if self.check_for_review(case):
            return []
        if newsigs:
            self.update_status(case, self.STATUS_OPEN)
        return []

    def clerk_review_case(self, case):
        """Clerk a "review" case (open for more than four days).

        A message will be set to the "very old notifiee", which is generally
        [[User talk:Szhang (WMF)]], if the case has been open for more than
        five days.
        """
        age = (datetime.utcnow() - case.file_time).total_seconds()
        if age > 60 * 60 * 24 * 5:
            if not case.very_old_notified:
                tmpl = self.tl_notify_stale
                title = case.title.replace("|", "&#124;")
                template = "{{subst:" + tmpl + "|" + title + "}}"
                miss = "<!-- Template:DRN stale notice | {0} -->".format(title)
                notice = _Notice(self.very_old_title, template, miss)
                case.very_old_notified = True
                msg = u"    {0}: will notify [[{1}]] with '{2}'"
                log = msg.format(case.id, self.very_old_title, template)
                self.logger.debug(log)
                return [notice]
        return []

    def clerk_closed_case(self, case, signatures):
        """Clerk a closed or resolved case.

        The case will be archived if it has been closed/resolved for more than
        one day and no edits have been made in the meantime. "Archiving" is
        the process of adding {{DRN archive top}}, {{DRN archive bottom}}, and
        removing the [[User:DoNotArchiveUntil]] comment.
        """
        if case.close_time == self.min_ts:
            case.close_time = datetime.utcnow()
        if case.archived:
            return
        timestamps = [timestamp for (editor, timestamp) in signatures]
        closed_age = (datetime.utcnow() - case.close_time).total_seconds()
        if timestamps:
            modify_age = (datetime.utcnow() - max(timestamps)).total_seconds()
        else:
            modify_age = 0
        if closed_age > 60 * 60 * 24 and modify_age > 60 * 60 * 24:
            arch_top = self.tl_archive_top
            arch_bottom = self.tl_archive_bottom
            reg = "<!-- \[\[User:DoNotArchiveUntil\]\] .*? -->(<!-- .*? -->)?"
            if re.search(reg, case.body):
                case.body = re.sub("\{\{" + arch_top + "\}\}", "", case.body)
                case.body = re.sub(reg, "{{" + arch_top + "}}", case.body)
            if not re.search(arch_bottom + "\s*\}\}\s*\Z", case.body):
                case.body += "\n{{" + arch_bottom + "}}"
            case.archived = True
            self.logger.debug(u"    {0}: archived case".format(case.id))

    def check_for_review(self, case):
        """Check whether a case is old enough to be set to "review"."""
        age = (datetime.utcnow() - case.file_time).total_seconds()
        if age > 60 * 60 * 24 * 4:
            self.update_status(case, self.STATUS_REVIEW)
            return True
        return False

    def update_status(self, case, new):
        """Safely update the status of a case, so we don't edit war."""
        old_n = self.ALIASES[case.status][0].upper()
        new_n = self.ALIASES[new][0].upper()
        old_n = "NEW" if not old_n else old_n
        new_n = "NEW" if not new_n else new_n
        if case.last_action != new:
            case.status = new
            log = u"    {0}: {1} -> {2}"
            self.logger.debug(log.format(case.id, old_n, new_n))
            return
        log = u"Avoiding {0} {1} -> {2} because we already did this ('{3}')"
        self.logger.info(log.format(case.id, old_n, new_n, case.title))

    def read_signatures(self, text):
        """Return a list of all parseable signatures in the body of a case.

        Signatures are returned as tuples of (editor, timestamp as datetime).
        """
        regex = r"\[\[(?:User(?:\stalk)?\:|Special\:Contributions\/)"
        regex += r"([^\n\[\]|]{,256}?)(?:\||\]\])"
        regex += r"(?!.*?(?:User(?:\stalk)?\:|Special\:Contributions\/).*?)"
        regex += r".{,256}?(\d{2}:\d{2},\s\d{1,2}\s\w+\s\d{4}\s\(UTC\))"
        matches = re.findall(regex, text, re.U|re.I)
        signatures = []
        for userlink, stamp in matches:
            username = userlink.split("/", 1)[0].replace("_", " ").strip()
            username = username[0].upper() + username[1:]
            if username == "DoNotArchiveUntil":
                continue
            stamp = stamp.strip()
            timestamp = datetime.strptime(stamp, "%H:%M, %d %B %Y (UTC)")
            signatures.append((username, timestamp))
        return signatures

    def get_signatures_from_db(self, conn, case):
        """Return a list of signatures in a case from the database.

        The return type is the same as read_signatures().
        """
        query = "SELECT signature_username, signature_timestamp FROM signatures WHERE signature_case = ?"
        with conn.cursor() as cursor:
            cursor.execute(query, (case.id,))
            return cursor.fetchall()

    def notify_parties(self, case):
        """Schedule notices to be sent to all parties of a case."""
        if case.parties_notified:
            return []

        notices = []
        template = "{{subst:" + self.tl_notify_party
        template += "|thread=" + case.title + "}} ~~~~"
        too_late = "<!--Template:DRN-notice-->"

        re_parties = "<span.*?>'''Users involved'''</span>(.*?)<span.*?>"
        text = re.search(re_parties, case.body, re.S|re.U)
        for line in text.group(1).splitlines():
            user = re.search("[:*#]{,5} \{\{User\|(.*?)\}\}", line)
            if user:
                party = user.group(1).replace("_", " ").strip()
                if party:
                    party = party[0].upper() + party[1:]
                    if party == case.file_user:
                        continue
                    notice = _Notice("User talk:" + party, template, too_late)
                    notices.append(notice)

        case.parties_notified = True
        log = u"    {0}: will try to notify {1} parties with '{2}'"
        self.logger.debug(log.format(case.id, len(notices), template))
        return notices

    def save_case_updates(self, conn, case, volunteers, sigs, storedsigs):
        """Save any updates made to a case and signatures in the database."""
        if case.status != case.original_status:
            case.last_action = case.status
            new = self.ALIASES[case.status][0]
            tl_status_esc = re.escape(self.tl_status)
            search = "\{\{" + tl_status_esc + "(\|?.*?)\}\}"
            repl = "{{" + self.tl_status + "|" + new + "}}"
            case.body = re.sub(search, repl, case.body)

        if sigs:
            newest_ts = max([stamp for (user, stamp) in sigs])
            newest_user = [usr for (usr, stamp) in sigs if stamp == newest_ts][0]
            case.modify_time = newest_ts
            case.modify_user = newest_user

        if any([usr in volunteers for (usr, stamp) in sigs]):
            newest_vts = max([stamp for (usr, stamp) in sigs if usr in volunteers])
            newest_vuser = [usr for (usr, stamp) in sigs if stamp == newest_vts][0]
            case.volunteer_time = newest_vts
            case.volunteer_user = newest_vuser

        if case.new:
            self.save_new_case(conn, case)
        else:
            self.save_existing_case(conn, case)

        with conn.cursor() as cursor:
            query1 = "DELETE FROM signatures WHERE signature_case = ? AND signature_username = ? AND signature_timestamp = ?"
            query2 = "INSERT INTO signatures (signature_case, signature_username, signature_timestamp) VALUES (?, ?, ?)"
            removals = set(storedsigs) - set(sigs)
            additions = set(sigs) - set(storedsigs)
            if removals:
                args = [(case.id, name, stamp) for (name, stamp) in removals]
                cursor.executemany(query1, args)
            if additions:
                args = []
                for name, stamp in additions:
                    args.append((case.id, name, stamp))
                cursor.executemany(query2, args)
            msg = u"    {0}: added {1} signatures and removed {2}"
            log = msg.format(case.id, len(additions), len(removals))
            self.logger.debug(log)

    def save_new_case(self, conn, case):
        """Save a brand new case to the database."""
        args = (case.id, case.title, case.status, case.last_action,
                case.file_user, case.file_time, case.modify_user,
                case.modify_time, case.volunteer_user, case.volunteer_time,
                case.close_time, case.parties_notified,
                case.very_old_notified, case.archived,
                case.last_volunteer_size)
        with conn.cursor() as cursor:
            query = "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, args)
        log = u"    {0}: inserted new case into database".format(case.id)
        self.logger.debug(log)

    def save_existing_case(self, conn, case):
        """Save an existing case to the database, updating as necessary."""
        with conn.cursor(oursql.DictCursor) as cursor:
            query = "SELECT * FROM cases WHERE case_id = ?"
            cursor.execute(query, (case.id,))
            stored = cursor.fetchone()

        with conn.cursor() as cursor:
            changes, args = [], []
            fields_to_check = [
                ("case_status", case.status),
                ("case_last_action", case.last_action),
                ("case_file_user", case.file_user),
                ("case_file_time", case.file_time),
                ("case_modify_user", case.modify_user),
                ("case_modify_time", case.modify_time),
                ("case_volunteer_user", case.volunteer_user),
                ("case_volunteer_time", case.volunteer_time),
                ("case_close_time", case.close_time),
                ("case_parties_notified", case.parties_notified),
                ("case_very_old_notified", case.very_old_notified),
                ("case_archived", case.archived),
                ("case_last_volunteer_size", case.last_volunteer_size)
            ]
            for column, data in fields_to_check:
                if data != stored[column]:
                    changes.append(column + " = ?")
                    args.append(data)
                    msg = u"    {0}: will alter {1} ('{2}' -> '{3}')"
                    log = msg.format(case.id, column, stored[column], data)
                    self.logger.debug(log)
            if changes:
                changes = ", ".join(changes)
                args.append(case.id)
                query = "UPDATE cases SET {0} WHERE case_id = ?".format(changes)
                cursor.execute(query, args)
            else:
                log = u"    {0}: no changes to commit".format(case.id)
                self.logger.debug(log)

    def save(self, page, cases, kwargs, start):
        """Save any changes to the noticeboard."""
        newtext = text = page.get()
        counter = 0
        for case in cases:
            if case.old != case.body:
                newtext = newtext.replace(case.old, case.body)
                counter += 1
        if newtext == text:
            self.logger.info(u"Nothing to edit on [[{0}]]".format(page.title))
            return True

        worktime = time() - start
        if worktime < 60:
            log = "Waiting {0} seconds to avoid edit conflicts"
            self.logger.debug(log.format(int(60 - worktime)))
            sleep(60 - worktime)
        page.reload()
        if page.get() != text:
            log = "Someone has edited the page while we were working; restarting"
            self.logger.warn(log)
            self.run(**kwargs)
            return False
        summary = self.clerk_summary.replace("$3", str(counter))
        summary = summary.replace("$4", "" if counter == 1 else "s")
        page.edit(newtext, summary, minor=True, bot=True)
        log = u"Saved page [[{0}]] ({1} updates)"
        self.logger.info(log.format(page.title, counter))
        return True

    def send_notices(self, site, notices):
        """Send out any templated notices to users or pages."""
        if not notices:
            self.logger.info("No notices to send")
            return
        for notice in notices:
            target, template = notice.target, notice.template
            log = u"Trying to notify [[{0}]] with '{1}'"
            self.logger.debug(log.format(target, template))
            page = site.get_page(target)
            if page.namespace == constants.NS_USER_TALK:
                user = site.get_user(target.split(":", 1)[1])
                if not user.exists and not user.is_ip:
                    log = u"Skipping [[{0}]]; user does not exist and is not an IP"
                    self.logger.info(log.format(target))
                    continue
            try:
                text = page.get()
            except exceptions.PageNotFoundError:
                text = ""
            if notice.too_late and notice.too_late in text:
                log = u"Skipping [[{0}]]; was already notified with '{1}'"
                self.logger.info(log.format(page.title, template))
                continue
            text += ("\n" if text else "") + template
            try:
                page.edit(text, self.notify_summary, minor=False, bot=True)
            except exceptions.EditError as error:
                name, msg = type(error).name, error.message
                log = u"Couldn't leave notice on [[{0}]] because of {1}: {2}"
                self.logger.error(log.format(page.title, name, msg))
            else:
                log = u"Notified [[{0}]] with '{1}'"
                self.logger.info(log.format(page.title, template))

        self.logger.debug("Done sending notices")

    def update_chart(self, conn, site):
        """Update the chart of open or recently closed cases."""
        page = site.get_page(self.chart_title)
        self.logger.info(u"Updating case status at [[{0}]]".format(page.title))
        statuses = self.compile_chart(conn)
        text = page.get()
        newtext = re.sub(u"<!-- status begin -->(.*?)<!-- status end -->",
                         "<!-- status begin -->\n" + statuses + "\n<!-- status end -->",
                         text, flags=re.DOTALL)
        if newtext == text:
            self.logger.info("Chart unchanged; not saving")
            return

        newtext = re.sub("<!-- sig begin -->(.*?)<!-- sig end -->",
                         "<!-- sig begin -->~~~ at ~~~~~<!-- sig end -->",
                         newtext)
        page.edit(newtext, self.chart_summary, minor=True, bot=True)
        self.logger.info(u"Chart saved to [[{0}]]".format(page.title))

    def compile_chart(self, conn):
        """Actually generate the chart from the database."""
        chart = "{{" + self.tl_chart_header + "|small={{{small|}}}}}\n"
        query = "SELECT * FROM cases WHERE case_status != ?"
        with conn.cursor(oursql.DictCursor) as cursor:
            cursor.execute(query, (self.STATUS_UNKNOWN,))
            for case in cursor:
                chart += self.compile_row(case)
        chart += "{{" + self.tl_chart_footer + "|small={{{small|}}}}}"
        return chart

    def compile_row(self, case):
        """Generate a single row of the chart from a dict via the database."""
        data = u"|t={case_title}|d={title}|s={case_status}"
        data += "|cu={case_file_user}|cs={file_sortkey}|ct={file_time}"
        if case["case_volunteer_user"]:
            data += "|vu={case_volunteer_user}|vs={volunteer_sortkey}|vt={volunteer_time}"
            case["volunteer_time"] = self.format_time(case["case_volunteer_time"])
            case["volunteer_sortkey"] = int(mktime(case["case_volunteer_time"].timetuple()))
        data += "|mu={case_modify_user}|ms={modify_sortkey}|mt={modify_time}"

        title = case["case_title"].replace("_", " ").replace("|", "&#124;")
        case["title"] = title[:47] + "..." if len(title) > 50 else title
        case["file_time"] = self.format_time(case["case_file_time"])
        case["file_sortkey"] = int(mktime(case["case_file_time"].timetuple()))
        case["modify_time"] = self.format_time(case["case_modify_time"])
        case["modify_sortkey"] = int(mktime(case["case_modify_time"].timetuple()))
        row = "{{" + self.tl_chart_row + data.format(**case)
        return row + "|sm={{{small|}}}}}\n"

    def format_time(self, dt):
        """Return a string telling the time since datetime occured."""
        parts = [("year", 31536000), ("day", 86400), ("hour", 3600)]
        seconds = int((datetime.utcnow() - dt).total_seconds())
        msg = []
        for name, size in parts:
            num = seconds // size
            seconds -= num * size
            if num:
                chunk = "{0} {1}".format(num, name if num == 1 else name + "s")
                msg.append(chunk)
        return ", ".join(msg) + " ago" if msg else "0 hours ago"

    def purge_old_data(self, conn):
        """Delete old cases (> six months) from the database."""
        log = "Purging closed cases older than six months from the database"
        self.logger.info(log)
        query = """DELETE cases, signatures
            FROM cases JOIN signatures ON case_id = signature_case
            WHERE case_status = ?
            AND case_file_time < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 180 DAY)
            AND case_modify_time < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 180 DAY)
        """
        with conn.cursor() as cursor:
            cursor.execute(query, (self.STATUS_UNKNOWN,))


class _Case(object):
    """A object representing a dispute resolution case."""
    def __init__(self, id_, title, status, last_action, file_user, file_time,
                 modify_user, modify_time, volunteer_user, volunteer_time,
                 close_time, parties_notified, archived, very_old_notified,
                 last_volunteer_size, new=False):
        self.id = id_
        self.title = title
        self.status = status
        self.last_action = last_action
        self.file_user = file_user
        self.file_time = file_time
        self.modify_user = modify_user
        self.modify_time = modify_time
        self.volunteer_user = volunteer_user
        self.volunteer_time = volunteer_time
        self.close_time = close_time
        self.parties_notified = parties_notified
        self.very_old_notified = very_old_notified
        self.archived = archived
        self.last_volunteer_size = last_volunteer_size
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
