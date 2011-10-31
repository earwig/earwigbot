# -*- coding: utf-8  -*-

from datetime import datetime
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
        self.pending_cat = cfg.get("pending", "Pending_AfC_submissions")
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
        if not action:
            return

        methods = {
            "save": self.save,
            "sync": self.sync,
            "edit": self.process_edit,
            "move": self.process_move,
            "delete": self.process_delete,
            "restore": self.process_edit,
        }

        method = methods.get(action)
        if method:
            try:
                method(**kwargs)
            finally:
                self.conn.close()            

    def save(self, **kwargs):
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
            return  # Don't edit the page if we're not adding anything

        newtext = re.sub("(<!-- sig begin -->)(.*?)(<!-- sig end -->)",
                         "\\1~~~ at ~~~~~\\3", newtext)
        page.edit(newtext, summary, minor=True, bot=True)

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
        with self.conn.cursor() as cursor, self.db_access_lock:
            self.sync_deleted(cursor)  # Remove deleted subs
            self.sync_oldids(cursor)   # Make sure all subs are up to date
            self.sync_pending(cursor)  # Add missing pending subs
            self.sync_old(cursor)      # Remove old declined and accepted subs

    def sync_deleted(self, cursor):
        query1 = "SELECT page_id FROM page"
        query2 = "SELECT page_id FROM page WHERE page_id = ?"
        cursor.execute(query1)
        for page in cursor:
            result = self.site.sql_query(query2, (page[0],))
            if not list(result):
                self.untrack_page(cursor, pageid=page[0])

    def sync_oldids(self, cursor):
        query1 = "SELECT page_id, page_title, page_modify_oldid FROM page"
        query2 = "SELECT page_latest, page_title FROM page WHERE page_id = ?"
        cursor.execute(query1)
        for page_id, title, oldid in cursor:
            result = list(self.site.sql_query(query2, (page_id,)))
            try:
                real_oldid = result[0][0]
                real_title = result[0][1]
            except IndexError:  # Page doesn't exist!
                self.untrack_page(cursor, pageid=page_id)
                continue
            if real_oldid != oldid:
                self.update_page(cursor, real_title)

    def sync_pending(self, cursor):
        query1 = """SELECT page_id FROM page JOIN row ON page_id = row_id
                    WHERE row_chart IN (1, 2, 3)"""
        query2 = """SELECT cl_from, page_title, page_namespace
                    FROM categorylinks JOIN page ON cl_from = page_id
                    WHERE cl_to = ?"""
        cursor.execute(query1)
        tracked = [i[0] for i in cursor.fetchall()]
        result = self.site.sql_query(query2, (self.pending_cat,))

        for pageid, title, ns in result:
            title = ":".join((self.site.namespace_id_to_name(ns), title))
            if title.replace("_", " ") in self.ignore_list:
                continue
            if pageid not in tracked:
                self.track_page(cursor, title)

    def sync_old(self, cursor):
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE row_chart IN (4, 5)
                   AND ADDTIME(page_special_time, '36:00:00')  < NOW()"""
        cursor.execute(query)

    def process_edit(self, page, **kwargs):
        if page in self.ignore_list:
            return
        with self.conn.cursor() as cursor, self.db_access_lock:
            self.sync_page(cursor, page)

    def process_move(self, page, **kwargs):
        query1 = "SELECT * FROM page WHERE page_title = ?"
        query2 = "SELECT page_latest FROM page WHERE page_namespace = ? AND page_title = ?"
        query3 = "UPDATE page SET page_title = ?, page_modify_oldid = ? WHERE page_title = ?"
        source, dest = page
        with self.conn.cursor() as cursor, self.db_access_lock:
            cursor.execute(query1, (source,))
            result = cursor.fetchall()
            if result:
                res = self.site.sql_query(query2, self.split_title(dest))
                try:
                    new_oldid = list(res)[0][0]
                except IndexError:
                    new_oldid = result[0][11]
                cursor.execute(query3, (dest, new_oldid, source))
            else:
                self.track_page(cursor, dest)

    def process_delete(self, page, **kwargs):
        query = "SELECT page_id FROM page WHERE page_namespace = ? AND page_title = ?"
        with self.conn.cursor() as cursor, self.db_access_lock:
            result = self.site.sql_query(query, self.split_title(page))
            if list(result):
                self.sync_page(cursor, page)
            else:
                self.untrack_page(cursor, title=page)

    def sync_page(self, cursor, page):
        query = "SELECT * FROM page WHERE page_title = ?"
        cursor.execute(query, (page,))
        result = cursor.fetchall()
        if result:
            self.update_page(cursor, page)
        else:
            self.track_page(cursor, page)

    def untrack_page(self, cursor, pageid=None, title=None):
        query = "DELETE FROM page, row USING page JOIN row ON page_id = row_id WHERE "
        if pageid:
            query += "page_id = ?"
            cursor.execute(query, (pageid,))
        elif title:
            query += "page_title = ?"
            cursor.execute(query, (title,))

    def track_page(self, cursor, title):
        """Update hook for when page is not in our database."""
        page = self.site.get_page(title)
        status, chart = self.get_status_and_chart(page)
        if not status or status in ("accept", "decline"):
            return

        pageid = page.pageid()
        title = page.title()
        short = self.get_short_title(title)
        size = len(page.get())
        notes = self.get_notes(page)
        c_user, c_time, c_id = self.get_create(pageid)
        m_user, m_time, m_id = self.get_modify(pageid)
        s_user, s_time, s_id = self.get_special(page, status)

        query1 = "INSERT INTO row VALUES (?, ?)"
        query2 = "INSERT INTO page VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(query1, (pageid, chart))
        cursor.execute(query2, (pageid, status, title, short, size, notes,
                                c_user, c_time, c_id, m_user, m_time, m_id,
                                s_user, s_time, s_id))

    def update_page(self, cursor, title):
        """Update hook for when page is in our database."""
        page = self.site.get_page(title)
        status, chart = self.get_status_and_chart(page)
        if not status:
            self.untrack_page(cursor, title=title)

        pageid = page.pageid()
        title = page.title()
        size = len(page.get())
        notes = self.get_notes(page)
        m_user, m_time, m_id = self.get_modify(pageid)

        query = "SELECT * FROM page JOIN row ON page_id = row_id WHERE page_id = ?"
        with self.conn.cursor(oursql.DictCursor) as dict_cursor:
            dict_cursor.execute(query, (pageid,))
            result = dict_cursor.fetchall()[0]

        if title != result["page_title"]:
            query = "UPDATE page SET page_title = ?, page_short = ? WHERE page_id = ?"
            short = self.get_short_title(title)
            cursor.execute(query, (title, short, pageid))

        if m_id != result["page_modify_oldid"]:
            query = """UPDATE page SET page_size = ?, page_modify_user = ?,
                       page_modify_time = ?, page_modify_oldid = ?
                       WHERE page_id = ?"""
            cursor.execute(query, (size, m_user, m_time, m_id, pageid))

        if status != result["page_status"]:
            query1 = """UPDATE page JOIN row ON page_id = row_id
                       SET page_status = ?, row_chart = ? WHERE page_id = ?"""
            query2 = """UPDATE page SET page_special_user = ?,
                       page_special_time = ?, page_special_oldid = ?
                       WHERE page_id = ?"""
            cursor.execute(query1, (status, chart, pageid))
            s_user, s_time, s_id = self.get_special(page, status)
            if s_id != result["page_special_oldid"]:
                cursor.execute(query2, (s_user, s_time, s_id, pageid))

        if notes != result["page_notes"]:
            query = "UPDATE page SET page_notes = ? WHERE page_id = ?"
            cursor.execute(query, (notes, pageid))

    def split_title(self, title):
        namespace, body = title.split(":", 1)[0]
        if not body:
            return 0, title
        try:
            ns = self.site.namespace_name_to_id(namespace)
        except wiki.NamespaceNotFoundError:
            return 0, title
        return ns, body

    def get_status_and_chart(self, page):
        content = page.get()
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
        query1 = "SELECT MIN(rev_id) FROM revision WHERE rev_page = ?"
        query2 = "SELECT rev_user_text, rev_timestamp, rev_id FROM revision WHERE rev_id = ?"
        result1 = self.site.sql_query(query1, (pageid,))
        rev_id = list(result1)[0][0]
        result2 = self.site.sql_query(query2, (rev_id,))
        m_user, m_time, m_id = list(result2)[0]
        return m_user, datetime.strptime(m_time, "%Y%m%d%H%M%S"), m_id

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
