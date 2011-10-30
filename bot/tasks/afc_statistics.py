# -*- coding: utf-8  -*-

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

        # Establish a connection with our SQL database:
        kwargs = cfg.get("sql", {})
        kwargs["read_default_file"] = expanduser("~/.my.cnf")
        self.conn = oursql.connect(**kwargs)
        self.db_access_lock = Lock()

    def run(self, **kwargs):
        self.site = wiki.get_site()

        action = kwargs.get("action")
        if not action:
            return

        methods = {
            "save": self.save,
            "sync", self.sync,
            "edit": self.process_edit,
            "move": self.process_move,
            "delete": self.process_delete,
            "restore": self.process_edit,
        }

        method = methods.get(action)
        if method:
            method(**kwargs)            

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
            self.sync_pending(cursor)  # Add missed pending subs
            self.sync_old(cursor)      # Remove old declined and accepted subs

    def sync_deleted(self, cursor):
        query1 = "SELECT page_id FROM page"
        query2 = "SELECT page_id FROM page WHERE page_id = ?"
        query3 = "DELETE FROM page JOIN row ON page_id = row_id WHERE page_id = ?"
        cursor.execute(query1)
        for page in cursor:
            result = self.site.sql_query(query2, (page,))
            if not list(result)[0]:
                cursor.execute(query3, (page,))

    def sync_oldids(self, cursor):
        query1 = "SELECT page_id, page_title, page_modify_oldid FROM page"
        query2 = "SELECT page_latest FROM page WHERE page_id = ?"
        query3 = "DELETE FROM page JOIN row ON page_id = row_id WHERE page_id = ?"
        cursor.execute(query1)
        for page_id, title, oldid in cursor:
            result = self.site.sql_query(query2, (page_id,))
            try:
                real_oldid = list(result)[0][0]
            except IndexError:  # Page doesn't exist!
                cursor.execute(query3, (page_id,))
                continue
            if real_oldid == oldid:
                continue
            self.update_page(cursor, title)

    def sync_pending(self, cursor):
        query = """SELECT page_title FROM page JOIN row ON page_id = row_id
                   WHERE row_chart IN (1, 2, 3)"""
        cursor.execute(query)
        tracked = [i[0] for i in cursor.fetchall()]
        
        category = self.site.get_category(self.pending_cat)
        for page in category.members(limit=500):
            if page in self.ignore_list:
                continue
            if page not in tracked:
                self.track_page(cursor, page)

    def sync_old(self, cursor):
        query = """DELETE FROM page, row USING page JOIN row
                   ON page_id = row_id WHERE row_chart IN (4, 5)
                   AND ADDTIME(page_special_time, '36:00:00')  < NOW()"""
        cursor.execute(query)

    def track_page(self, cursor, page):
        # Page update hook when page is not in our database.
        pass

    def update_page(self, cursor, page):
        # Page update hook when page is in our database.
        pass

    def process_edit(self, page, **kwargs):
        query = "SELECT * FROM page WHERE page_title = ?"
        with self.conn.cursor() as cursor, self.db_access_lock:
            cursor.execute(query, (page,))
            result = cursor.fetchall()
            if result:
                self.update_page(cursor, page)
            else:
                self.track_page(cursor, page)

    def process_move(self, page, **kwargs):
        query1 = "SELECT * FROM page WHERE page_title = ?"
        query2 = "SELECT page_latest FROM page WHERE page_title = ?"
        query3 = "UPDATE page SET page_title = ?, page_modify_oldid = ? WHERE page_title = ?"
        source, dest = page
        with self.conn.cursor() as cursor, self.db_access_lock:
            cursor.execute(query1, (source,))
            result = cursor.fetchall()
            if not result:
                self.track_page(cursor, page)
            else:
                try:
                    new_oldid = list(self.site.sql_query(query2, (dest,)))[0][0]
                except IndexError:
                    new_oldid = result[11]
                cursor.execute(query3, (dest, new_oldid, source))

    def process_delete(self, page, **kwargs):
        query1 = "SELECT page_id FROM page WHERE page_title = ?"
        query2 = "DELETE FROM page JOIN row ON page_id = row_id WHERE page_title = ?"
        with self.conn.cursor() as cursor, self.db_access_lock:
            result = self.site.sql_query(query1, (page,))
            if not list(result)[0]:
                cursor.execute(query2, (page,))
                return                
        self.process_edit(page)
