# -*- coding: utf-8  -*-

from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import count
from os.path import expanduser
from threading import Lock
from time import sleep

from matplotlib import pyplot as plt
from numpy import arange
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
    used to generate a graph showing the number of AfC submissions by date
    with matplotlib and numpy. The chart is saved as a PNG to
    config.tasks["afc_history"]["graph"]["dest"], which defaults to
    "afc_history.png".
    """
    name = "afc_history"

    def __init__(self):
        cfg = config.tasks.get(self.name, {})
        self.num_days = cfg.get("days", 90)
        self.categories = cfg.get("categories", {})

        # Graph stuff:
        self.graph = cfg.get("graph", {})
        self.destination = self.graph.get("dest", "afc_history.png")

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
                num_days = int(kwargs.get("days", self.num_days))
                if action == "update":
                    self.update(num_days)
                elif action == "generate":
                    self.generate(num_days)
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

    def generate(self, num_days):
        self.logger.info("Generating chart for past {0} days".format(num_days))
        data = OrderedDict()
        generator = self.backwards_cat_iterator()
        for d in xrange(num_days):
            category = generator.next()
            date = category.title().split("/")[-1]
            data[date] = self.get_date_counts(date)

        dest = expanduser(self.destination)
        self.generate_chart(reversed(data))
        plt.savefig(dest)
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

        q_select = "SELECT page_date, page_status FROM page WHERE page_id = ?"
        q_delete = "DELETE FROM page WHERE page_id = ?"
        q_update = "UPDATE page SET page_date = ?, page_status = ? WHERE page_id = ?"
        q_insert = "INSERT INTO page VALUES (?, ?, ?)"
        members = category.members(use_sql=True)

        with self.conn.cursor() as cursor:
            for title, pageid in members:
                cursor.execute(q_select, (pageid,))
                stored = cursor.fetchall()
                status = self.get_status(title, pageid)

                if status == STATUS_NONE:
                    if stored:
                        cursor.execute(q_delete, (pageid,))
                    continue

                if stored:
                    stored_date, stored_status = list(stored)[0]
                    if date != stored_date or status != stored_status:
                        cursor.execute(q_update, (date, status, pageid))

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
        sq = self.site.sql_query
        query = "SELECT 1 FROM categorylinks WHERE cl_to = ? AND cl_from = ?"
        match = lambda cat: list(sq(query, (cat.replace(" ", "_"), pageid)))

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

    def generate_chart(self, data):
        pends = [d[STATUS_PEND] for d in data.itervalues()]
        declines = [d[STATUS_DECLINE] for d in data.itervalues()]
        accepts = [d[STATUS_ACCEPT] for d in data.itervalues()]
        ind = arange(len(data))
        width = self.graph.get("width", 0.75)
        xstep = self.graph.get("xAxisStep", 6)
        xticks = arange(xstep-1, ind.size+xstep-1, xstep) + width/2.0
        xlabels = [d for c, d in zip(count(1), data.keys()) if not c % xstep]
        pcolor = self.graph.get("pendingColor", "y")
        dcolor = self.graph.get("declinedColor", "r")
        acolor = self.graph.get("acceptedColor", "g")

        p1 = plt.bar(ind, pends, width, color=pcolor)
        p2 = plt.bar(ind, declines, width, color=dcolor, bottom=pends)
        p3 = plt.bar(ind, accepts, width, color=acolor, bottom=declines)

        plt.title("AfC submissions per date")
        plt.ylabel("Submissions")
        plt.xlabel("Date")
        plt.xticks(xticks, xlabels)
        plt.legend((p1[0], p2[0], p3[0]), ("Pending", "Declined", "Accepted"))

        fig = plt.gcf()
        fig.set_size_inches(12, 9)  # 1200, 900
        fig.autofmt_xdate()
