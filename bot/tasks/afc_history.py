# -*- coding: utf-8  -*-

from datetime import datetime, timedelta
from os.path import expanduser
from threading import Lock
from time import sleep

import oursql

from classes import BaseTask
import config
import wiki

# Valid submission statuses:
STATUS_NONE = 0
STATUS_PEND = 1
STATUS_DECLINE = 2
STATUS_ACCEPT = 3

class Task(BaseTask):
    """A task to generate charts about AfC submissions over time.

    The main function of the task is to work through the "AfC submissions by
    date" categories (e.g. [[Category:AfC submissions by date/12 July 2011]])
    and determine the number of declined, accepted, and currently pending
    submissions every day.

    This information is saved to a MySQL database ("u_earwig_afc_history") and
    used to generate attractive graphs showing the number of AfC submissions
    over time.
    """
    name = "afc_history"

    def __init__(self):
        cfg = config.tasks.get(self.name, {})
        self.destination = cfg.get("destination", "afc_history.png")
        self.categories = cfg.get("categories", {})

        # Connection data for our SQL database:
        kwargs = cfg.get("sql", {})
        kwargs["read_default_file"] = expanduser("~/.my.cnf")
        self.conn_data = kwargs
        self.db_access_lock = Lock()

    def run(self, **kwargs):
        self.site = wiki.get_site()
        with self.db_access_lock:
            self.conn = oursql.connect(**self.conn_data)
            
            action = kwargs.get("action")
            try:
                if action == "update":
                    self.update(kwargs.get("days", 90))
                elif action == "generate":
                    self.generate(kwargs.get("days", 90))
            finally:
                self.conn.close()

    def update(self, num_days):
        self.logger.info("Updating past {0} days".format(num_days))
        generator = self.backwards_cat_iterator()
        for d in xrange(num_days):
            category = generator.next()
            date = category.title().split("/")[-1]
            self.update_date(date, category)
            sleep(15)
        self.logger.info("Update complete")

    def generate(self, data):
        self.logger.info("Generating chart for past {0} days".format(num_days))
        data = {}
        generator = self.backwards_cat_iterator()
        for d in xrange(num_days):
            category = generator.next()
            date = category.title().split("/")[-1]
            data[date] = self.get_date_counts(date)

        dest = expanduser(self.destination)
        with open(dest, "wb") as fp:
            fp.write(data)
        self.logger.info("Chart saved to {0}".format(dest))

    def backwards_cat_iterator(self):
        date_base = self.categories["dateBase"]
        current = datetime.utcnow()
        while 1:
            subcat = current.strftime("%d %B %Y")
            title = "/".join((date_base, subcat))
            yield self.site.get_category(title)
            current -= timedelta(1)  # Subtract one day from date

    def update_date(self, date, category):
        msg = "Updating {0} ([[{1}]])".format(date, category.title())
        self.logger.debug(msg)

        q_select = "SELECT page_id, page_status FROM page WHERE page_date = ?"
        q_delete = "DELETE FROM page WHERE page_id = ?"
        q_update = "UPDATE page SET page_status = ? WHERE page_id = ?"
        q_insert = "INSERT INTO page VALUES (?, ?, ?)"
        members = category.members(use_sql=True)
        tracked = []
        statuses = {}

        with self.conn.cursor() as cursor:
            cursor.execute(q_select, (date,))
            for pageid, status in cursor:
                tracked.append(pageid)
                statuses[pageid] = status

            for title, pageid in members:
                status = self.get_status(title, pageid)
                if status == STATUS_NONE:
                    if pageid in tracked:
                        cursor.execute(q_delete, (pageid,))
                    continue
                if pageid in tracked:
                    if status != statuses[pageid]:
                        cursor.execute(q_update, (status, pageid))
                else:
                    cursor.execute(q_insert, (pageid, date, status))

    def get_status(self, title, pageid):
        page = self.site.get_page(title)
        ns = page.namespace()

        if ns == wiki.NS_FILE_TALK:  # Ignore accepted FFU requests
            return STATUS_NONE

        if ns == wiki.NS_TALK:
            new_page = page.toggle_talk()
            if new_page.is_redirect():
                return STATUS_NONE  # Ignore accepted AFC/R requests
            return STATUS_ACCEPT

        cats = self.categories
        query = "SELECT 1 FROM categorylinks WHERE cl_from = ? AND cl_to = ?"
        match = lambda cat: list(self.site.sql_query(query, (cat, pageid)))

        if match(cats["pending"]):
            return STATUS_PEND
        elif match(cats["unsubmitted"]):
            return STATUS_NONE
        elif match(cats["declined"]):
            return STATUS_DECLINE
        return STATUS_NONE

    def get_date_counts(self, date):
        query = "SELECT COUNT(*) FROM page WHERE page_date = ? AND page_status = ?"
        statuses = [STATUS_PEND, STATUS_DECLINE, STATUS_ACCEPT]
        counts = {}
        with self.conn.cursor() as cursor:
            for status in statuses:
                cursor.execute(query, (date, status))
                count = cursor.fetchall()[0][0]
                counts[status] = count
        return counts
