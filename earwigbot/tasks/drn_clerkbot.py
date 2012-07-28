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

import oursql

from earwigbot.tasks import Task

class DRNClerkBot(Task):
    """A task to clerk for [[WP:DRN]]."""
    name = "drn_clerkbot"
    number = 19

    def setup(self):
        """Hook called immediately after the task is loaded."""
        cfg = self.config.tasks.get(self.name, {})
        self.title = cfg.get("page", "Wikipedia:Dispute resolution noticeboard")

        # Templates used in chart generation:
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
        self.db_access_lock = Lock()

    def run(self, **kwargs):
        """Entry point for a task event."""
        page = self.bot.wiki.get_site().get_page(self.title)
