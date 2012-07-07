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

from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import count
from os.path import expanduser
from threading import Lock
from time import sleep

from matplotlib import pyplot as plt
from numpy import arange
import oursql

from earwigbot import wiki
from earwigbot.tasks import Task

class AFCHistory(Task):
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

    # Valid submission statuses:
    STATUS_NONE = 0
    STATUS_PEND = 1
    STATUS_DECLINE = 2
    STATUS_ACCEPT = 3

    def setup(self):
        cfg = self.config.tasks.get(self.name, {})
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
        self.site = self.bot.wiki.get_site()
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
        for i in xrange(num_days):
            category = generator.next()
            date = category.title.split("/")[-1]
            self.update_date(date, category)
            sleep(10)
        self.logger.info("Update complete")

    def generate(self, num_days):
        self.logger.info("Generating chart for past {0} days".format(num_days))
        data = OrderedDict()
        generator = self.backwards_cat_iterator()
        for i in xrange(num_days):
            category = generator.next()
            date = category.title.split("/")[-1]
            data[date] = self.get_date_counts(date)

        data = OrderedDict(reversed(data.items()))  # Oldest to most recent
        self.generate_chart(data)
        dest = expanduser(self.destination)
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
        msg = "Updating {0} ([[{1}]])".format(date, category.title)
        self.logger.debug(msg)

        q_select = "SELECT page_date, page_status FROM page WHERE page_id = ?"
        q_delete = "DELETE FROM page WHERE page_id = ?"
        q_update = "UPDATE page SET page_date = ?, page_status = ? WHERE page_id = ?"
        q_insert = "INSERT INTO page VALUES (?, ?, ?)"
        members = category.get_members()

        with self.conn.cursor() as cursor:
            for title, pageid in members:
                cursor.execute(q_select, (pageid,))
                stored = cursor.fetchall()
                status = self.get_status(title, pageid)

                if status == self.STATUS_NONE:
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
        ns = page.namespace

        if ns == wiki.NS_FILE_TALK:  # Ignore accepted FFU requests
            return self.STATUS_NONE

        if ns == wiki.NS_TALK:
            new_page = page.toggle_talk()
            sleep(2)
            if new_page.is_redirect:
                return self.STATUS_NONE  # Ignore accepted AFC/R requests
            return self.STATUS_ACCEPT

        cats = self.categories
        sq = self.site.sql_query
        query = "SELECT 1 FROM categorylinks WHERE cl_to = ? AND cl_from = ?"
        match = lambda cat: list(sq(query, (cat.replace(" ", "_"), pageid)))

        if match(cats["pending"]):
            return self.STATUS_PEND
        elif match(cats["unsubmitted"]):
            return self.STATUS_NONE
        elif match(cats["declined"]):
            return self.STATUS_DECLINE
        return self.STATUS_NONE

    def get_date_counts(self, date):
        query = "SELECT COUNT(*) FROM page WHERE page_date = ? AND page_status = ?"
        statuses = [self.STATUS_PEND, self.STATUS_DECLINE, self.STATUS_ACCEPT]
        counts = {}
        with self.conn.cursor() as cursor:
            for status in statuses:
                cursor.execute(query, (date, status))
                count = cursor.fetchall()[0][0]
                counts[status] = count
        return counts

    def generate_chart(self, data):
        plt.title(self.graph.get("title", "AfC submissions by date"))
        plt.xlabel(self.graph.get("xaxis", "Date"))
        plt.ylabel(self.graph.get("yaxis", "Submissions"))

        pends = [d[self.STATUS_PEND] for d in data.itervalues()]
        declines = [d[self.STATUS_DECLINE] for d in data.itervalues()]
        accepts = [d[self.STATUS_ACCEPT] for d in data.itervalues()]
        pends_declines = [p + d for p, d in zip(pends, declines)]
        ind = arange(len(data))
        xsize = self.graph.get("xsize", 1200)
        ysize = self.graph.get("ysize", 900)
        width = self.graph.get("width", 1)
        xstep = self.graph.get("xAxisStep", 6)
        pcolor = self.graph.get("pendingColor", "#f0e460")
        dcolor = self.graph.get("declinedColor", "#f291a6")
        acolor = self.graph.get("acceptedColor", "#81fc4c")

        p1 = plt.bar(ind, pends, width, color=pcolor)
        p2 = plt.bar(ind, declines, width, color=dcolor, bottom=pends)
        p3 = plt.bar(ind, accepts, width, color=acolor, bottom=pends_declines)

        xticks = arange(xstep-1, ind.size+xstep-1, xstep) + width/2.0
        xlabels = [d for c, d in zip(count(1), data.keys()) if not c % xstep]
        plt.xticks(xticks, xlabels)
        plt.yticks(arange(0, plt.ylim()[1], 10))
        plt.tick_params(direction="out")

        leg = plt.legend((p1[0], p2[0], p3[0]), ("Pending", "Declined",
                         "Accepted"), loc="upper left", fancybox=True)
        leg.get_frame().set_alpha(0.5)

        fig = plt.gcf()
        fig.set_size_inches(xsize/100, ysize/100)
        fig.autofmt_xdate()

        ax = plt.gca()
        ax.yaxis.grid(True)
