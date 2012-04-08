# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from os.path import expanduser

import oursql

from earwigbot.commands import BaseCommand

class Command(BaseCommand):
    """Return the replag for a specific database on the Toolserver."""
    name = "replag"

    def process(self, data):
        args = {}
        if not data.args:
            args["db"] = "enwiki_p"
        else:
            args["db"] = data.args[0]
        args["host"] = args["db"].replace("_", "-") + ".rrdb.toolserver.org"
        args["read_default_file"] = expanduser("~/.my.cnf")

        conn = oursql.connect(**args)
        with conn.cursor() as cursor:
            query = "SELECT UNIX_TIMESTAMP() - UNIX_TIMESTAMP(rc_timestamp) FROM recentchanges ORDER BY rc_timestamp DESC LIMIT 1"
            cursor.execute(query)
            replag = int(cursor.fetchall()[0][0])
        conn.close()

        msg = "Replag on \x0302{0}\x0301 is \x02{1}\x0F seconds."
        self.reply(data, msg.format(args["db"], replag))
