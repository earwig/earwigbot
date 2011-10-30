# -*- coding: utf-8  -*-

import re
from os.path import expanduser
from time import strftime, strptime

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

    def run(self, **kwargs):
        self.site = wiki.get_site()
        
        action = kwargs.get("action")
        if not action:
            return
        if action == "save":
            self.save()
            return

        page = kwargs.get("page")
        if page:
            methods = {
                "edit": self.process_edit,
                "move": self.process_move,
                "delete": self.process_delete,
                "restore": self.process_restore,
            }
            method = methods.get(action)
            if method:
                method(page)

    def save(self):
        self.check_integrity()

        if self.shutoff_enabled():
            return

        statistics = self.compile_charts()

        page = self.site.get_page(self.pagename)
        text = page.get()
        newtext = re.sub("(<!-- stat begin -->)(.*?)(<!-- stat end -->)",
                         statistics.join(("\\1", "\\3")), text,
                         flags=re.DOTALL)
        if newtext == text:
            return  # Don't edit the page if we're not adding anything

        newtext = re.sub("(<!-- sig begin -->)(.*?)(<!-- sig end -->)",
                         "\\1~~~ at ~~~~~\\3", newtext)
        page.edit(newtext, self.summary, minor=True, bot=True)

    def compile_charts(self):
        stats = ""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM chart")
            charts = cursor.fetchall()
            for chart_info in charts:
                stats += self.compile_chart(chart_info) + "\n"
        return stats[:-1]  # Drop the last newline

    def compile_chart(self, chart_info):
        chart_id, chart_title, special_title = chart_info

        if special_title:
            chart = "{{{0}|{1}|{2}}}".format(self.tl_header, chart_title, special_title)
        else:
            chart = "{{{0}|{1}}}".format(self.tl_header, chart_title)

        query = "SELECT * FROM page JOIN row ON page_id = row_id WHERE row_chart = ?"
        with self.conn.cursor(oursql.DictCursor) as cursor:
            cursor.execute(query, (chart_id,))
            for page in cursor:
                chart += "\n" + self.compile_chart_row(page)

        chart += "\n{{{0}}}".format(self.tl_footer)
        return chart

    def compile_chart_row(self, page):
        row = "{{{0}|s={page_status}|t={page_title}|h={page_short}|z={page_size}|"
        row += "cr={page_create_user}|cd={page_create_time}|ci={page_create_oldid}|"
        row += "mr={page_modify_user}|md={page_modify_time}|mi={page_modify_oldid}|"

        page["page_create_time"] = self.format_timestamp(page["page_create_time"])
        page["page_modify_time"] = self.format_timestamp(page["page_modify_time"])

        if page["page_special_user"]:
            row += "sr={page_special_user}|sd={page_special_time}|si={page_special_oldid}|"
            page["page_special_time"] = self.format_timestamp(page["page_special_time"])

        if page["page_notes"]:
            row += "n=1{page_notes}"

        row += "}}"
        return row.format(self.tl_row, **page)

    def format_timestamp(self, ts):
        return strftime("%H:%M, %d %B %Y", strptime(ts, "%Y-%m-%d %H:%M:%S"))

    def check_integrity(self):
        pass

    def process_edit(self, page):
        pass

    def process_move(self, page):
        pass

    def process_delete(self, page):
        pass

    def process_restore(self, page):
        pass
