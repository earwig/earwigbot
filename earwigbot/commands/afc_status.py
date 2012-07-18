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

import re

from earwigbot.commands import Command

class AFCStatus(Command):
    """Get the number of pending AfC submissions, open redirect requests, and
    open file upload requests."""
    name = "status"
    commands = ["status", "count", "num", "number"]
    hooks = ["join", "msg"]

    def check(self, data):
        if data.is_command and data.command in self.commands:
            return True
        try:
            if data.line[1] == "JOIN" and data.chan == "#wikipedia-en-afc":
                if data.nick != self.config.irc["frontend"]["nick"]:
                    return True
        except IndexError:
            pass
        return False

    def process(self, data):
        self.site = self.bot.wiki.get_site()

        if data.line[1] == "JOIN":
            status = " ".join(("\x02Current status:\x0F", self.get_status()))
            self.notice(data.nick, status)
            return

        if data.args:
            action = data.args[0].lower()
            if action.startswith("sub") or action == "s":
                subs = self.count_submissions()
                msg = "There are \x0305{0}\x0F pending AfC submissions (\x0302WP:AFC\x0F)."
                self.reply(data, msg.format(subs))

            elif action.startswith("redir") or action == "r":
                redirs = self.count_redirects()
                msg = "There are \x0305{0}\x0F open redirect requests (\x0302WP:AFC/R\x0F)."
                self.reply(data, msg.format(redirs))

            elif action.startswith("file") or action == "f":
                files = self.count_redirects()
                msg = "There are \x0305{0}\x0F open file upload requests (\x0302WP:FFU\x0F)."
                self.reply(data, msg.format(files))

            elif action.startswith("agg") or action == "a":
                try:
                    agg_num = int(data.args[1])
                except IndexError:
                    agg_data = (self.count_submissions(),
                                self.count_redirects(), self.count_files())
                    agg_num = self.get_aggregate_number(agg_data)
                except ValueError:
                    msg = "\x0303{0}\x0F isn't a number!"
                    self.reply(data, msg.format(data.args[1]))
                    return
                aggregate = self.get_aggregate(agg_num)
                msg = "Aggregate is \x0305{0}\x0F (AfC {1})."
                self.reply(data, msg.format(agg_num, aggregate))

            elif action.startswith("nocolor") or action == "n":
                self.reply(data, self.get_status(color=False))

            else:
                msg = "Unknown argument: \x0303{0}\x0F. Valid args are 'subs', 'redirs', 'files', 'agg', 'nocolor'."
                self.reply(data, msg.format(data.args[0]))

        else:
            self.reply(data, self.get_status())

    def get_status(self, color=True):
        subs = self.count_submissions()
        redirs = self.count_redirects()
        files = self.count_files()
        agg_num = self.get_aggregate_number((subs, redirs, files))
        aggregate = self.get_aggregate(agg_num)

        if color:
            msg = "Articles for creation {0} (\x0302AFC\x0F: \x0305{1}\x0F; \x0302AFC/R\x0F: \x0305{2}\x0F; \x0302FFU\x0F: \x0305{3}\x0F)."
        else:
            msg = "Articles for creation {0} (AFC: {1}; AFC/R: {2}; FFU: {3})."
        return msg.format(aggregate, subs, redirs, files)

    def count_submissions(self):
        """Returns the number of open AFC submissions (count of CAT:PEND)."""
        # Subtract two for [[Wikipedia:Articles for creation/Redirects]] and
        # [[Wikipedia:Files for upload]], which aren't real submissions:
        return self.site.get_category("Pending AfC submissions").pages - 2

    def count_redirects(self):
        """Returns the number of open redirect submissions. Calculated as the
        total number of submissions minus the closed ones."""
        title = "Wikipedia:Articles for creation/Redirects"
        content = self.site.get_page(title).get()
        total = len(re.findall("^\s*==(.*?)==\s*$", content, re.MULTILINE))
        closed = content.lower().count("{{afc-c|b}}")
        redirs = total - closed
        return redirs

    def count_files(self):
        """Returns the number of open WP:FFU (Files For Upload) requests.
        Calculated as the total number of requests minus the closed ones."""
        content = self.site.get_page("Wikipedia:Files for upload").get()
        total = len(re.findall("^\s*==(.*?)==\s*$", content, re.MULTILINE))
        closed = content.lower().count("{{ifu-c|b}}")
        files = total - closed
        return files

    def get_aggregate(self, num):
        """Returns a human-readable AFC status based on the number of pending
        AFC submissions, open redirect requests, and open FFU requests. This
        does not match {{AFC status}} directly because the algorithm factors in
        WP:AFC/R and WP:FFU while the template only looks at the main
        submissions. The reasoning is that AFC/R and FFU are still part of
        the project, so even if there are no pending submissions, a backlog at
        FFU (for example) indicates that our work is *not* done and the
        project-wide backlog is most certainly *not* clear."""
        if num == 0:
            return "is \x02\x0303clear\x0F"
        elif num <= 200:
            return "is \x0303almost clear\x0F"
        elif num <= 400:
            return "is \x0312normal\x0F"
        elif num <= 600:
            return "is \x0307lightly backlogged\x0F"
        elif num <= 900:
            return "is \x0304backlogged\x0F"
        elif num <= 1200:
            return "is \x02\x0304heavily backlogged\x0F"
        else:
            return "is \x02\x1F\x0304severely backlogged\x0F"

    def get_aggregate_number(self, (subs, redirs, files)):
        """Returns an 'aggregate number' based on the real number of pending
        submissions in CAT:PEND (subs), open redirect submissions in WP:AFC/R
        (redirs), and open files-for-upload requests in WP:FFU (files)."""
        num = subs + (redirs / 2) + (files / 2)
        return num
