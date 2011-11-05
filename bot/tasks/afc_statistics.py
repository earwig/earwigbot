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
        self.site = wiki.get_site()
        self.conn = oursql.connect(**self.conn_data)

        action = kwargs.get("action")
        try:
            if action == "save":
                self.save()
            elif action == "sync":
                self.sync()
        finally:
            self.conn.close()            

    def save(self, **kwargs):
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
        stats = ""
        with self.conn.cursor() as cursor, self.db_access_lock:
            cursor.execute("SELECT * FROM chart")
            for chart in cursor:
                stats += self.compile_chart(chart) + "\n"
        return stats[:-1]  # Drop the last newline

    def compile_chart(self, chart_info):
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
        return timestamp.strftime("%H:%M, %d %B %Y")

    def sync(self, **kwargs):
        self.logger.info("Starting sync")
        self.report_replag()
        with self.conn.cursor() as cursor, self.db_access_lock:
            self.update_tracked(cursor)
            self.add_untracked(cursor)
            self.delete_old(cursor)
        self.logger.info("Sync completed")

    def report_replag(self):
        replag = self.site.get_replag()
        if replag < 60:
            lvl = logging.DEBUG
        elif replag < 720:
            lvl = logging.INFO
        else:
            lvl = logging.WARNING
        self.logger.log(lvl, "Server replag is {0}".format(replag))

    def update_tracked(self, cursor):
        self.logger.debug("Updating tracked submissions")
        query1 = "SELECT page_id, page_title, page_modify_oldid FROM page"
        query2 = "SELECT page_latest, page_title FROM page WHERE page_id = ?"
        cursor.execute(query1)
        for pageid, title, oldid in cursor:
            msg = "Updating tracked page: [[{0}]] (id: {1}) @ {2}"
            self.logger.debug(msg.format(pageid, title, oldid))
            result = list(self.site.sql_query(query2, (pageid,)))
            try:
                real_oldid = result[0][0]
                real_title = result[0][1]
            except IndexError:  # Page doesn't exist!
                self.untrack_page(cursor, pageid)
                continue
            if real_oldid != oldid:
                self.update_page(cursor, pageid, real_title)

    def add_untracked(self, cursor):
        self.logger.debug("Adding untracked pending submissions")
        cursor.execute("SELECT page_id FROM page")
        tracked = [i[0] for i in cursor.fetchall()]

        category = self.site.get_category(self.pending_cat)
        pending = category.members(limit=500)

        for title, pageid in pending:
            if title in self.ignore_list:
                continue
            if pageid not in tracked:
                self.track_page(cursor, pageid, title)

    def delete_old(self, cursor):
        self.logger.debug("Removing old submissions from chart")
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE row_chart IN (4, 5)
                   AND ADDTIME(page_special_time, '36:00:00')  < NOW()"""
        cursor.execute(query)

    def untrack_page(self, cursor, pageid):
        self.logger.debug("Untracking page (id: {0})".format(pageid))
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE page_id = ?"""
        cursor.execute(query, (pageid,))

    def track_page(self, cursor, pageid, title):
        """Update hook for when page is not in our database."""
        msg = "Tracking page [[{0}]] (id: {1})".format(title, pageid)
        self.logger.debug(msg)

        page = self.site.get_page(title)
        status, chart = self.get_status_and_chart(page)
        if not status:
            msg = "Could not find a status for [[{0}]]".format(title)
            self.logger.warn(msg)
            return

        title = page.title()
        short = self.get_short_title(title)
        size = len(page.get())
        notes = self.get_notes(page)
        c_user, c_time, c_id = self.get_create(pageid)
        m_user, m_time, m_id = self.get_modify(pageid)
        s_user, s_time, s_id = self.get_special(page, status)

        query1 = "INSERT INTO row VALUES ?"
        query2 = "INSERT INTO page VALUES ?"
        cursor.execute(query1, ((pageid, chart),))
        cursor.execute(query2, ((pageid, status, title, short, size, notes,
                                c_user, c_time, c_id, m_user, m_time, m_id,
                                s_user, s_time, s_id),))

    def update_page(self, cursor, pageid, title):
        """Update hook for when page is in our database."""
        msg = "Updating page [[{0}]] (id: {1})".format(title, pageid)
        self.logger.debug(msg)

        page = self.site.get_page(title)
        status, chart = self.get_status_and_chart(page)
        if not status:
            self.untrack_page(cursor, pageid)

        if pageid != page.pageid():
            msg = "Page [[{0}]] is not what it should be! (id: {0} != {1})"
            self.logger.warn(msg.format(pageid, page.pageid()))
            self.report_replag()
            self.untrack_page(cursor, pageid)

        title = page.title()
        size = len(page.get())
        notes = self.get_notes(page)
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
            self.update_page_special(cursor, result, pageid, status, chart, page)

        if notes != result["page_notes"]:
            self.update_page_notes(cursor, result, pageid, notes)

    def update_page_title(self, cursor, result, pageid, title):
        query = "UPDATE page SET page_title = ?, page_short = ? WHERE page_id = ?"
        short = self.get_short_title(title)
        cursor.execute(query, (title, short, pageid))
        msg = "{0}: title: {1} -> {2}"
        self.logger.debug(msg.format(pageid, result["page_title"], title))

    def update_page_modify(self, cursor, result, pageid, size, m_user, m_time, m_id):
        query = """UPDATE page SET page_size = ?, page_modify_user = ?,
                   page_modify_time = ?, page_modify_oldid = ?
                   WHERE page_id = ?"""
        cursor.execute(query, (size, m_user, m_time, m_id, pageid))

        msg = "{0}: modify: {1} / {2} / {3} -> {4} / {5} / {6}"
        msg = msg.format(pageid, result["page_modify_user"],
                         result["page_modify_time"],
                         result["page_modify_oldid"], m_user, m_time, m_id)
        self.logger.debug(msg)

    def update_page_special(self, cursor, result, pageid, status, chart, page):
        query1 = """UPDATE page JOIN row ON page_id = row_id
                   SET page_status = ?, row_chart = ? WHERE page_id = ?"""
        query2 = """UPDATE page SET page_special_user = ?,
                   page_special_time = ?, page_special_oldid = ?
                   WHERE page_id = ?"""
        cursor.execute(query1, (status, chart, pageid))

        msg = "{0}: status: {1} ({2}) -> {3} ({4})"
        self.logger.debug(msg.format(pageid, result["page_status"],
                                     result["row_chart"], status, chart))

        s_user, s_time, s_id = self.get_special(page, status)

        if s_id != result["page_special_oldid"]:
            cursor.execute(query2, (s_user, s_time, s_id, pageid))
            msg = "{0}: special: {1} / {2} / {3} -> {4} / {5} / {6}"
            msg = msg.format(pageid, result["page_special_user"],
                             result["page_special_time"],
                             result["page_special_oldid"], m_user, m_time, m_id)
            self.logger.debug(msg)

    def update_page_notes(self, cursor, result, pageid, notes):
        query = "UPDATE page SET page_notes = ? WHERE page_id = ?"
        cursor.execute(query, (notes, pageid))
        msg = "{0}: notes: {1} -> {2}"
        self.logger.debug(msg.format(pageid, result["page_notes"], notes))

    def get_status_and_chart(self, page):
        try:
            content = page.get()
        except wiki.PageNotFoundError:
            msg = "Page [[{0}]] does not exist, but the server said it should!"
            self.logger.warn(msg.format(page.title()))
            return None, 0

        if page.is_redirect():
            target = page.get_redirect_target()
            if self.site.get_page(target).namespace() == 0:
                return "accept", 4
            return None, 0
        elif re.search("\{\{afc submission\|r\|(.*?)\}\}", content, re.I):
            return "review", 3
        elif re.search("\{\{afc submission\|h\|(.*?)\}\}", content, re.I):
            return "pend", 2
        elif re.search("\{\{afc submission\|\|(.*?)\}\}", content, re.I):
            return "pend", 1
        elif re.search("\{\{afc submission\|t\|(.*?)\}\}", content, re.I):
            return None, 0
        elif re.search("\{\{afc submission\|d\|(.*?)\}\}", content, re.I):
            return "decline", 5
        return None, 0

    def get_short_title(self, title):
        short = re.sub("Wikipedia(\s*talk)?\:Articles\sfor\screation\/", "", title)
        if len(short) > 50:
            short = "".join((short[:47], "..."))
        return short

    def get_create(self, pageid):
        query = """SELECT rev_user_text, rev_timestamp, rev_id
                   FROM revision WHERE rev_id =
                   (SELECT MIN(rev_id) FROM revision WHERE rev_page = ?)"""
        result = self.site.sql_query(query, (pageid,))
        c_user, c_time, c_id = list(result)[0]
        return c_user, datetime.strptime(c_time, "%Y%m%d%H%M%S"), c_id

    def get_modify(self, pageid):
        query = """SELECT rev_user_text, rev_timestamp, rev_id FROM revision
                   JOIN page ON rev_id = page_latest WHERE page_id = ?"""
        result = self.site.sql_query(query, (pageid,))
        m_user, m_time, m_id = list(result)[0]
        return m_user, datetime.strptime(m_time, "%Y%m%d%H%M%S"), m_id

    def get_special(self, page, status):
        return None, None, None

    def get_notes(self, page):
        return None
