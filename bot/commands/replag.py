# -*- coding: utf-8  -*-

from os.path import expanduser

import oursql

from classes import BaseCommand

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
            cursor.execute("SELECT NOW() - MAX(rev_timestamp) FROM revision")
            replag = int(cursor.fetchall()[0][0])
        conn.close()

        msg = "Replag on \x0302{0}\x0301 is \x02{1}\x0F seconds."
        self.connection.reply(data, msg.format(args["db"], replag))
