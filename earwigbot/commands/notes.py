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

from earwigbot.commands import Command

class Notes(Command):
    """A mini IRC-based wiki for storing notes, tips, and reminders."""
    name = "notes"

    def process(self, data):
        pass


class OldCommand(object):
    def parse(self):
        if command == "notes" or command == "note" or command == "about" or command == "data" or command == "database":
            try:
                action = line2[4]
            except BaseException:
                reply("What do you want me to do? Type \"!notes help\" for more information.", chan, nick)
                return
            import MySQLdb
            db = MySQLdb.connect(db="u_earwig_ircbot", host="sql", read_default_file="/home/earwig/.my.cnf")
            specify = ' '.join(line2[5:])
            if action == "help" or action == "manual":
                shortCommandList = "read, write, change, undo, delete, move, author, category, list, report, developer"
                if specify == "read":
                    say("To read an entry, type \"!notes read <entry>\".", chan)
                elif specify == "write":
                    say("To write a new entry, type \"!notes write <entry> <content>\". This will create a new entry only if one does not exist, see the below command...", chan)
                elif specify == "change":
                    say("To change an entry, type \"!notes change <entry> <new content>\". The old entry will be stored in the database, so it can be undone later.", chan)
                elif specify == "undo":
                    say("To undo a change, type \"!notes undo <entry>\".", chan)
                elif specify == "delete":
                    say("To delete an entry, type \"!notes delete <entry>\". For security reasons, only bot admins can do this.", chan)
                elif specify == "move":
                    say("To move an entry, type \"!notes move <old_title> <new_title>\".", chan)
                elif specify == "author":
                    say("To return the author of an entry, type \"!notes author <entry>\".", chan)
                elif specify == "category" or specify == "cat":
                    say("To change an entry's category, type \"!notes category <entry> <category>\".", chan)
                elif specify == "list":
                    say("To list all categories in the database, type \"!notes list\". Type \"!notes list <category>\" to get all entries in a certain category.", chan)
                elif specify == "report":
                    say("To give some statistics about the mini-wiki, including some debugging information, type \"!notes report\" in a PM.", chan)
                elif specify == "developer":
                    say("To do developer work, such as writing to the database directly, type \"!notes developer <command>\". This can only be done by the bot owner.", chan)
                else:
                    db.query("SELECT * FROM version;")
                    r = db.use_result()
                    data = r.fetch_row(0)
                    version = data[0]
                    reply("The Earwig Mini-Wiki: running v%s." % version, chan, nick)
                    reply("The full list of commands, for reference, are: %s." % shortCommandList, chan, nick)
                    reply("For an explaination of a certain command, type \"!notes help <command>\".", chan, nick)
                    reply("You can also access the database from the Toolserver: http://toolserver.org/~earwig/cgi-bin/irc_database.py", chan, nick)
                    time.sleep(0.4)
                return
            elif action == "read":
                specify = string.lower(specify)
                if " " in specify: specify = string.split(specify, " ")[0]
                if not specify or "\"" in specify:
                    reply("Please include the name of the entry you would like to read after the command, e.g. !notes read earwig", chan, nick)
                    return
                try:
                    db.query("SELECT entry_content FROM entries WHERE entry_title = \"%s\";" % specify)
                    r = db.use_result()
                    data = r.fetch_row(0)
                    entry = data[0][0]
                    say("Entry \"\x02%s\x0F\": %s" % (specify, entry), chan)
                except Exception:
                    reply("There is no entry titled \"\x02%s\x0F\"." % specify, chan, nick)
                return
            elif action == "delete" or action == "remove":
                specify = string.lower(specify)
                if " " in specify: specify = string.split(specify, " ")[0]
                if not specify or "\"" in specify:
                    reply("Please include the name of the entry you would like to delete after the command, e.g. !notes delete earwig", chan, nick)
                    return
                if authy == "owner" or authy == "admin":
                    try:
                        db.query("DELETE from entries where entry_title = \"%s\";" % specify)
                        r = db.use_result()
                        db.commit()
                        reply("The entry on \"\x02%s\x0F\" has been removed." % specify, chan, nick)
                    except Exception:
                        phenny.reply("Unable to remove the entry on \"\x02%s\x0F\", because it doesn't exist." % specify, chan, nick)
                else:
                    reply("Only bot admins can remove entries.", chan, nick)
                return
            elif action == "developer":
                if authy == "owner":
                    db.query(specify)
                    r = db.use_result()
                    try:
                        print r.fetch_row(0)
                    except Exception:
                        pass
                    db.commit()
                    reply("Done.", chan, nick)
                else:
                    reply("Only the bot owner can modify the raw database.", chan, nick)
                return
            elif action == "write":
                try:
                    write = line2[5]
                    content = ' '.join(line2[6:])
                except Exception:
                    reply("Please include some content in your entry.", chan, nick)
                    return
                db.query("SELECT * from entries WHERE entry_title = \"%s\";" % write)
                r = db.use_result()
                data = r.fetch_row(0)
                if data:
                    reply("An entry on %s already exists; please use \"!notes change %s %s\"." % (write, write, content), chan, nick)
                    return
                content2 = content.replace('"', '\\' + '"')
                db.query("INSERT INTO entries (entry_title, entry_author, entry_category, entry_content, entry_content_old) VALUES (\"%s\", \"%s\", \"uncategorized\", \"%s\", NULL);" % (write, nick, content2))
                db.commit()
                reply("You have written an entry titled \"\x02%s\x0F\", with the following content: \"%s\"" % (write, content), chan, nick)
                return
            elif action == "change":
                reply("NotImplementedError", chan, nick)
            elif action == "undo":
                reply("NotImplementedError", chan, nick)
            elif action == "move":
                reply("NotImplementedError", chan, nick)
            elif action == "author":
                try:
                    entry = line2[5]
                except Exception:
                    reply("Please include the name of the entry you would like to get information for after the command, e.g. !notes author earwig", chan, nick)
                    return
                db.query("SELECT entry_author from entries WHERE entry_title = \"%s\";" % entry)
                r = db.use_result()
                data = r.fetch_row(0)
                if data:
                    say("The author of \"\x02%s\x0F\" is \x02%s\x0F." % (entry, data[0][0]), chan)
                    return
                reply("There is no entry titled \"\x02%s\x0F\"." % entry, chan, nick)
                return
            elif action == "cat" or action == "category":
                reply("NotImplementedError", chan, nick)
            elif action == "list":
                reply("NotImplementedError", chan, nick)
            elif action == "report":
                reply("NotImplementedError", chan, nick)
