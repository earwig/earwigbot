# -*- coding: utf-8  -*-

from datetime import datetime
import logging
import re
from os.path import expanduser
from threading import Lock

import oursql

from classes import BaseTask
import config
import wiki

# Chart status number constants:
CHART_NONE = 0
CHART_PEND = 1
CHART_DRAFT = 2
CHART_REVIEW = 3
CHART_ACCEPT = 4
CHART_DECLINE = 5

class Task(BaseTask):
    """A task to generate statistics for WikiProject Articles for Creation.

    Statistics are stored in a MySQL database ("u_earwig_afc_statistics")
    accessed with oursql. Statistics are updated live while watching the recent
    changes IRC feed and saved once an hour, on the hour, to self.pagename.
    In the live bot, this is "Template:AFC statistics".
    """
    name = "afc_statistics"
    number = 2

    def __init__(self):
        self.cfg = cfg = config.tasks.get(self.name, {})

        # Set some wiki-related attributes:
        self.pagename = cfg.get("page", "Template:AFC statistics")
        self.pending_cat = cfg.get("pending", "Pending AfC submissions")
        self.ignore_list = cfg.get("ignore_list", [])
        default_summary = "Updating statistics for [[WP:WPAFC|WikiProject Articles for creation]]."
        self.summary = self.make_summary(cfg.get("summary", default_summary))

        # Templates used in chart generation:
        templates = cfg.get("templates", {})
        self.tl_header = templates.get("header", "AFC statistics/header")
        self.tl_row = templates.get("row", "AFC statistics/row")
        self.tl_footer = templates.get("footer", "AFC statistics/footer")

        # Connection data for our SQL database:
        kwargs = cfg.get("sql", {})
        kwargs["read_default_file"] = expanduser("~/.my.cnf")
        self.conn_data = kwargs
        self.db_access_lock = Lock()

    def run(self, **kwargs):
        """Entry point for a task event.

        Depending on the kwargs passed, we will either synchronize our local
        statistics database with the site (self.sync()) or save it to the wiki
        (self.save()). We will additionally create an SQL connection with our
        local database.
        """
        self.site = wiki.get_site()
        self.conn = oursql.connect(**self.conn_data)

        action = kwargs.get("action")
        try:
            if action == "save":
                self.save(**kwargs)
            elif action == "sync":
                self.sync(**kwargs)
        finally:
            self.conn.close()

    def save(self, **kwargs):
        """Save our local statistics to the wiki.

        After checking for emergency shutoff, the statistics chart is compiled,
        and then saved to self.pagename using self.summary iff it has changed
        since last save.
        """
        self.logger.info("Saving chart")
        if kwargs.get("fromIRC"):
            summary = " ".join((self.summary, "(!earwigbot)"))
        else:
            if self.shutoff_enabled():
                return
            summary = self.summary

        statistics = self.compile_charts()

        page = self.site.get_page(self.pagename)
        text = page.get()
        newtext = re.sub("(<!-- stat begin -->)(.*?)(<!-- stat end -->)",
                         statistics.join(("\\1\n", "\n\\3")), text,
                         flags=re.DOTALL)
        if newtext == text:
            self.logger.info("Chart unchanged; not saving")
            return  # Don't edit the page if we're not adding anything

        newtext = re.sub("(<!-- sig begin -->)(.*?)(<!-- sig end -->)",
                         "\\1~~~ at ~~~~~\\3", newtext)
        page.edit(newtext, summary, minor=True, bot=True)
        self.logger.info("Chart saved to [[{0}]]".format(page.title()))

    def compile_charts(self):
        """Compile and return all statistics information from our local db."""
        stats = ""
        with self.conn.cursor() as cursor, self.db_access_lock:
            cursor.execute("SELECT * FROM chart")
            for chart in cursor:
                stats += self.compile_chart(chart) + "\n"
        return stats[:-1]  # Drop the last newline

    def compile_chart(self, chart_info):
        """Compile and return a single statistics chart."""
        chart_id, chart_title, special_title = chart_info

        chart = "|".join((self.tl_header, chart_title))
        if special_title:
            chart += "".join(("|", special_title))
        chart = "".join(("{{", chart, "}}"))

        query = "SELECT * FROM page JOIN row ON page_id = row_id WHERE row_chart = ?"
        with self.conn.cursor(oursql.DictCursor) as cursor:
            cursor.execute(query, (chart_id,))
            for page in cursor:
                chart += "\n" + self.compile_chart_row(page)

        chart += "".join(("\n{{", self.tl_footer, "}}"))
        return chart

    def compile_chart_row(self, page):
        """Compile and return a single chart row.

        'page' is a dict of page information, taken as a row from the page
        table, where keys are column names and values are their cell contents.
        """
        row = "{0}|s={page_status}|t={page_title}|h={page_short}|z={page_size}|"
        row += "cr={page_create_user}|cd={page_create_time}|ci={page_create_oldid}|"
        row += "mr={page_modify_user}|md={page_modify_time}|mi={page_modify_oldid}|"

        page["page_create_time"] = self.format_time(page["page_create_time"])
        page["page_modify_time"] = self.format_time(page["page_modify_time"])

        if page["page_special_user"]:
            row += "sr={page_special_user}|sd={page_special_time}|si={page_special_oldid}|"
            page["page_special_time"] = self.format_time(page["page_special_time"])

        if page["page_notes"]:
            row += "n=1{page_notes}"

        return "".join(("{{", row.format(self.tl_row, **page), "}}"))

    def format_time(self, timestamp):
        """Format a datetime into the standard MediaWiki timestamp format."""
        return timestamp.strftime("%H:%M, %d %B %Y")

    def sync(self, **kwargs):
        """Synchronize our local statistics database with the site.

        Syncing involves, in order, updating tracked submissions that have
        been changed since last sync (self.update_tracked()), adding pending
        submissions that are not tracked (self.add_untracked()), and removing
        old submissions from the database (self.delete_old()).

        The sync will be canceled if SQL replication lag is greater than 600
        seconds, because this will lead to potential problems and outdated
        data, not to mention putting demand on an already overloaded server.
        Giving sync the kwarg "ignore_replag" will go around this restriction.
        """
        self.logger.info("Starting sync")

        replag = self.site.get_replag()
        self.logger.debug("Server replag is {0}".format(replag))
        if replag > 600 and not kwargs.get("ignore_replag"):
            msg = "Sync canceled as replag ({0} secs) is greater than ten minutes."
            self.logger.warn(msg.format(replag))

        with self.conn.cursor() as cursor, self.db_access_lock:
            self.update_tracked(cursor)
            self.add_untracked(cursor)
            self.delete_old(cursor)

        self.logger.info("Sync completed")

    def update_tracked(self, cursor):
        """Update tracked submissions that have been changed since last sync.

        This is done by iterating through every page in our database and
        comparing our stored latest revision ID with the actual latest revision
        ID from an SQL query. If they differ, we will update our information
        about the page (self.update_page()).

        If the page does not exist, we will remove it from our database with
        self.untrack_page().
        """
        self.logger.debug("Updating tracked submissions")
        query1 = "SELECT page_id, page_title, page_modify_oldid FROM page"
        query2 = """SELECT page_latest, page_title, page_namespace FROM page
                    WHERE page_id = ?"""
        cursor.execute(query1)
        for pageid, title, oldid in cursor:
            msg = "Updating tracked page: [[{0}]] (id: {1}) @ {2}"
            self.logger.debug(msg.format(pageid, title, oldid))
            result = list(self.site.sql_query(query2, (pageid,)))
            try:
                real_oldid = result[0][0]
            except IndexError:  # Page doesn't exist!
                self.untrack_page(cursor, pageid)
                continue
            if real_oldid != oldid:
                body = result[0][1].replace("_", " ")
                ns = self.site.namespace_id_to_name(result[0][2])
                real_title = ":".join(ns, body)
                self.update_page(cursor, pageid, real_title)

    def add_untracked(self, cursor):
        """Add pending submissions that are not yet tracked.

        This is done by compiling a list of all currently tracked submissions
        and iterating through all members of self.pending_cat via SQL. If a
        page in the pending category is not tracked and is not in
        self.ignore_list, we will track it with self.track_page().
        """
        self.logger.debug("Adding untracked pending submissions")
        cursor.execute("SELECT page_id FROM page")
        tracked = [i[0] for i in cursor.fetchall()]

        category = self.site.get_category(self.pending_cat)
        pending = category.members(use_sql=True)

        for title, pageid in pending:
            if title in self.ignore_list:
                continue
            if pageid not in tracked:
                self.track_page(cursor, pageid, title)

    def delete_old(self, cursor):
        """Remove old submissions from the database.

        "Old" is defined as a submission that has been declined or accepted
        more than 36 hours ago. Pending submissions cannot be "old".
        """
        self.logger.debug("Removing old submissions from chart")
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE row_chart IN ?
                   AND ADDTIME(page_special_time, '36:00:00')  < NOW()"""
        old_charts = (CHART_ACCEPT, CHART_DECLINE)
        cursor.execute(query, (old_charts,))

    def untrack_page(self, cursor, pageid):
        """Remove a page, given by ID, from our database."""
        self.logger.debug("Untracking page (id: {0})".format(pageid))
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE page_id = ?"""
        cursor.execute(query, (pageid,))

    def track_page(self, cursor, pageid, title):
        """Update hook for when page is not in our database.

        A variety of SQL queries are used to gather information about the page,
        which are then saved to our database.
        """
        msg = "Tracking page [[{0}]] (id: {1})".format(title, pageid)
        self.logger.debug(msg)

        content = self.get_content(title)
        status, chart = self.get_status_and_chart(content)
        if not status:
            msg = "Could not find a status for [[{0}]]".format(title)
            self.logger.error(msg)
            return

        short = self.get_short_title(title)
        size = len(content)
        notes = self.get_notes(pageid)
        c_user, c_time, c_id = self.get_create(pageid)
        m_user, m_time, m_id = self.get_modify(pageid)
        s_user, s_time, s_id = self.get_special(pageid, chart)

        query1 = "INSERT INTO row VALUES ?"
        query2 = "INSERT INTO page VALUES ?"
        cursor.execute(query1, ((pageid, chart),))
        cursor.execute(query2, ((pageid, status, title, short, size, notes,
                                c_user, c_time, c_id, m_user, m_time, m_id,
                                s_user, s_time, s_id),))

    def update_page(self, cursor, pageid, title):
        """Update hook for when page is already in our database.

        A variety of SQL queries are used to gather information about the page,
        which is compared against our stored information. Differing information
        is then updated.

        If our page is now a redirect, we will determine the namespace it was
        moved to. If it was moved to the mainspace or template space, we will
        set the sub's status as accepted. If it was to the Project: or Project
        talk: namespaces, we'll merely update our stored title (this is likely
        to occur if a submission was moved from the userspace to the project
        space). If it was moved to another namespace, something unusual has
        happened, and we'll untrack the submission.
        """
        msg = "Updating page [[{0}]] (id: {1})".format(title, pageid)
        self.logger.debug(msg)

        content = self.get_content(title)
        try:
            redirect_regex = wiki.Page.re_redirect
            target_title = re.findall(redirect_regex, content, flags=re.I)[0]
        except IndexError:
            status, chart = self.get_status_and_chart(content)
            if not status:
                self.untrack_page(cursor, pageid)
                return
        else:
            target_ns = self.site.get_page(target_title).namespace()
            if target_ns in [wiki.NS_MAIN, wiki.NS_TEMPLATE]:
                status, chart = "accept", CHART_ACCEPT
            elif target_ns in [wiki.NS_PROJECT, wiki.NS_PROJECT_TALK]:
                title = target_title
                content = self.get_content(title)
                status, chart = self.get_status_and_chart(content)
                if not status:
                    self.untrack_page(cursor, pageid)
                    return
            else:
                msg = "Page has moved to namespace {0}".format(target_ns)
                self.logger.debug(msg)
                self.untrack_page(cursor, pageid)
                return

        size = len(content)
        notes = self.get_notes(pageid)
        m_user, m_time, m_id = self.get_modify(pageid)

        query = "SELECT * FROM page JOIN row ON page_id = row_id WHERE page_id = ?"
        with self.conn.cursor(oursql.DictCursor) as dict_cursor:
            dict_cursor.execute(query, (pageid,))
            result = dict_cursor.fetchall()[0]

        if title != result["page_title"]:
            self.update_page_title(cursor, result, pageid, title)

        if m_id != result["page_modify_oldid"]:
            self.update_page_modify(cursor, result, pageid, size, m_user, m_time, m_id)

        if status != result["page_status"]:
            self.update_page_status(cursor, result, pageid, status, chart, page)

        if notes != result["page_notes"]:
            self.update_page_notes(cursor, result, pageid, notes)

    def update_page_title(self, cursor, result, pageid, title):
        """Update the title and short_title of a page in our database."""
        query = "UPDATE page SET page_title = ?, page_short = ? WHERE page_id = ?"
        short = self.get_short_title(title)
        cursor.execute(query, (title, short, pageid))
        msg = "{0}: title: {1} -> {2}"
        self.logger.debug(msg.format(pageid, result["page_title"], title))

    def update_page_modify(self, cursor, result, pageid, size, m_user, m_time, m_id):
        """Update the last modified information of a page in our database."""
        query = """UPDATE page SET page_size = ?, page_modify_user = ?,
                   page_modify_time = ?, page_modify_oldid = ?
                   WHERE page_id = ?"""
        cursor.execute(query, (size, m_user, m_time, m_id, pageid))

        msg = "{0}: modify: {1} / {2} / {3} -> {4} / {5} / {6}"
        msg = msg.format(pageid, result["page_modify_user"],
                         result["page_modify_time"],
                         result["page_modify_oldid"], m_user, m_time, m_id)
        self.logger.debug(msg)

    def update_page_status(self, cursor, result, pageid, status, chart, page):
        """Update the status and "specialed" information of a page."""
        query1 = """UPDATE page JOIN row ON page_id = row_id
                   SET page_status = ?, row_chart = ? WHERE page_id = ?"""
        query2 = """UPDATE page SET page_special_user = ?,
                   page_special_time = ?, page_special_oldid = ?
                   WHERE page_id = ?"""
        cursor.execute(query1, (status, chart, pageid))

        msg = "{0}: status: {1} ({2}) -> {3} ({4})"
        self.logger.debug(msg.format(pageid, result["page_status"],
                                     result["row_chart"], status, chart))

        s_user, s_time, s_id = self.get_special(pageid, chart)

        if s_id != result["page_special_oldid"]:
            cursor.execute(query2, (s_user, s_time, s_id, pageid))
            msg = "{0}: special: {1} / {2} / {3} -> {4} / {5} / {6}"
            msg = msg.format(pageid, result["page_special_user"],
                             result["page_special_time"],
                             result["page_special_oldid"], m_user, m_time, m_id)
            self.logger.debug(msg)

    def update_page_notes(self, cursor, result, pageid, notes):
        """Update the notes (or warnings) of a page in our database."""
        query = "UPDATE page SET page_notes = ? WHERE page_id = ?"
        cursor.execute(query, (notes, pageid))
        msg = "{0}: notes: {1} -> {2}"
        self.logger.debug(msg.format(pageid, result["page_notes"], notes))

    def get_content(self, title):
        """Get the current content of a page by title from SQL.

        The page's current revision ID is retrieved from SQL, and then
        site.get_revid_content() is called.

        The reason a more conventional method (i.e. site.get_page.get()) is
        avoided is that due to replication lag, a discrepancy between the live
        database (which the API uses) and the replicated database (which SQL
        uses) can lead to incorrect and very confusing data, such as missing
        pages that are supposed to exist, if both are used interchangeably.
        """
        query = "SELECT page_latest FROM page WHERE page_title = ? AND page_namespace = ?"
        namespace, base = title.split(":", 1)
        try:
            ns = self.site.namespace_name_to_id(namespace)
        except wiki.NamespaceNotFoundError:
            base = title
            ns = wiki.NS_MAIN

        result = self.site.sql_query(query, (base, ns))
        revid = list(result)[0]
        return self.site.get_revid_content(revid)

    def get_status_and_chart(self, content):
        """Determine the status and chart number of an AFC submission.

        The methodology used here is the same one I've been using for years
        (see also commands.afc_report), but with the new draft system taken
        into account. The order here is important: if there is more than one
        {{AFC submission}} template on a page, we need to know which one to
        use (revision history search to find the most recent isn't a viable
        idea :P).
        """
        if re.search("\{\{afc submission\|r\|(.*?)\}\}", content, re.I):
            return "review", CHART_REVIEW
        elif re.search("\{\{afc submission\|h\|(.*?)\}\}", content, re.I):
            return "pend", CHART_DRAFT
        elif re.search("\{\{afc submission\|\|(.*?)\}\}", content, re.I):
            return "pend", CHART_PEND
        elif re.search("\{\{afc submission\|t\|(.*?)\}\}", content, re.I):
            return None, CHART_NONE
        elif re.search("\{\{afc submission\|d\|(.*?)\}\}", content, re.I):
            return "decline", CHART_DECLINE
        return None, CHART_NONE

    def get_short_title(self, title):
        """Shorten a title so we can display it in a chart using less space.

        Basically, this just means removing the "Wikipedia talk:Articles for
        creation" part from the beginning. If it is longer than 50 characters,
        we'll shorten it down to 47 and add an poor-man's ellipsis at the end.
        """
        short = re.sub("Wikipedia(\s*talk)?\:Articles\sfor\screation\/", "", title)
        if len(short) > 50:
            short = "".join((short[:47], "..."))
        return short

    def get_create(self, pageid):
        """Return information about a page's first edit ("creation").

        This consists of the page creator, creation time, and the earliest
        revision ID.
        """
        query = """SELECT rev_user_text, rev_timestamp, rev_id
                   FROM revision WHERE rev_id =
                   (SELECT MIN(rev_id) FROM revision WHERE rev_page = ?)"""
        result = self.site.sql_query(query, (pageid,))
        c_user, c_time, c_id = list(result)[0]
        return c_user, datetime.strptime(c_time, "%Y%m%d%H%M%S"), c_id

    def get_modify(self, pageid):
        """Return information about a page's last edit ("modification").

        This consists of the most recent editor, modification time, and the
        lastest revision ID.
        """
        query = """SELECT rev_user_text, rev_timestamp, rev_id FROM revision
                   JOIN page ON rev_id = page_latest WHERE page_id = ?"""
        result = self.site.sql_query(query, (pageid,))
        m_user, m_time, m_id = list(result)[0]
        return m_user, datetime.strptime(m_time, "%Y%m%d%H%M%S"), m_id

    def get_special(self, pageid, chart):
        """Return information about a page's "special" edit.

        I tend to use the term "special" as a verb a lot, which is bound to
        cause confusion. It is merely a short way of saying "the edit in which
        a declined submission was declined, an accepted submission was
        accepted, a submission in review was set as such, and a pending draft
        was submitted."

        This "information" consists of the special edit's editor, its time, and
        its revision ID. If the page's status is not something that involves
        "special"-ing, we will return None for all three. The same will be
        returned if we cannot determine when the page was "special"-ed, or if
        it was "special"-ed more than 100 edits ago.
        """
        if chart in [CHART_NONE, CHART_PEND]:
            return None, None, None
        elif chart == CHART_ACCEPT:
            return self.get_create(pageid)
        elif chart == CHART_DRAFT:
            search = "(?!\{\{afc submission\|h\|(.*?)\}\})"
        elif chart == CHART_REVIEW:
            search = "(?!\{\{afc submission\|r\|(.*?)\}\})"
        elif chart == CHART_DECLINE:
            search = "(?!\{\{afc submission\|d\|(.*?)\}\})"

        query = """SELECT rev_user_text, rev_timestamp, rev_id
                   FROM revision WHERE rev_page = ? ORDER BY rev_id DESC"""
        result = self.site.sql_query(query, (pageid,))

        counter = 0
        for user, ts, revid in result:
            counter += 1
            if counter > 100:
                break
            content = self.site.get_revid_content(revid)
            if re.search(search, content, re.I):
                return user, datetime.strptime(ts, "%Y%m%d%H%M%S"), revid

        return None, None, None

    def get_notes(self, pageid):
        """Return any special notes or warnings about this page.

        Currently unimplemented, so always returns None.
        """
        return None
