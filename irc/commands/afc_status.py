# -*- coding: utf-8  -*-

"""Report the status of AFC submissions, either as an automatic message on join
or a request via !status."""

import re

from core import config
from irc.classes import BaseCommand
from wiki import tools

class AFCStatus(BaseCommand):
    def get_hooks(self):
        return ["join", "msg"]

    def get_help(self, command):
        return "Get the number of pending AfC submissions, open redirect requests, and open file upload requests."

    def check(self, data):
        if data.is_command and data.command in ["status", "count", "num", "number", "afc_status"]:
            return True
        try:
            if data.line[1] == "JOIN" and data.chan == "#wikipedia-en-afc":
                if data.nick != config.irc["frontend"]["nick"]:
                    return True
        except IndexError:
            pass
        return False

    def process(self, data):
        self.site = tools.get_site()

        if data.line[1] == "JOIN":
            notice = self.get_join_notice()
            self.connection.notice(data.nick, notice)
            return

        if data.args:
            action = data.args[0].lower()
            if action.startswith("sub") or action == "s":
                subs = self.count_submissions()
                self.connection.reply(data, "there are currently %s pending AfC submissions." % subs)

            elif action.startswith("redir") or action == "r":
                redirs = self.count_redirects()
                self.connection.reply(data, "there are currently %s open redirect requests." % redirs)

            elif action.startswith("file") or action == "f":
                files = self.count_redirects()
                self.connection.reply(data, "there are currently %s open file upload requests." % files)

            elif action.startswith("agg") or action == "a":
                try:
                    agg_num = int(data.args[1])
                except IndexError:
                    agg_data = (self.count_submissions(), self.count_redirects(), self.count_files())
                    agg_num = self.get_aggregate_number(agg_data)
                except ValueError:
                    self.connection.reply(data, "\x0303%s\x0301 isn't a number!" % data.args[1])
                    return
                aggregate = self.get_aggregate(agg_num)
                self.connection.reply(data, "aggregate is currently %s (AfC %s)." % (agg_num, aggregate))

            elif action.startswith("join") or action == "j":
                notice = self.get_join_notice()
                self.connection.reply(data, notice)

            else:
                self.connection.reply(data, "unknown argument: \x0303%s\x0301. Valid args are 'subs', 'redirs', 'files', 'agg', and 'join'." % data.args[0])

        else:
            subs = self.count_submissions()
            redirs = self.count_redirects()
            files = self.count_files()
            self.connection.reply(data, "there are currently %s pending submissions, %s open redirect requests, and %s open file upload requests."
                    % (subs, redirs, files))

    def get_join_notice(self):
        subs = self.count_submissions()
        redirs = self.count_redirects()
        files = self.count_files()
        agg_num = self.get_aggregate_number((subs, redirs, files))
        aggregate = self.get_aggregate(agg_num)
        return ("\x02Current status:\x0F Articles for Creation %s (\x0302AFC\x0301: \x0305%s\x0301; \x0302AFC/R\x0301: \x0305%s\x0301; \x0302FFU\x0301: \x0305%s\x0301)"
                % (aggregate, subs, redirs, files))

    def count_submissions(self):
        """Returns the number of open AFC submissions (count of CAT:PEND)."""
        cat = self.site.get_category("Pending AfC submissions")
        subs = cat.get_members(limit=500)
        subs -= 2 # remove [[Wikipedia:Articles for creation/Redirects]] and [[Wikipedia:Files for upload]], which aren't real submissions
        return subs

    def count_redirects(self):
        """Returns the number of open redirect submissions. Calculated as the
        total number of submissions minus the closed ones."""
        content = self.site.get_page("Wikipedia:Articles for creation/Redirects").get()
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
        does not match {{AFC status}} directly because my algorithm factors in
        WP:AFC/R and WP:FFU while the template only looks at the main
        submissions. My reasoning is that AFC/R and FFU are still part of
        the project, so even if there are no pending submissions, a backlog at
        FFU (for example) indicates that our work is *not* done and the
        project-wide backlog is most certainly *not* clear."""
        if num == 0:
            return "is \x02\x0303clear\x0301\x0F"
        elif num < 125:  # < 25 subs
            return "is \x0303almost clear\x0301"
        elif num < 200:  # < 40 subs
            return "is \x0312normal\x0301"
        elif num < 275:  # < 55 subs
            return "is \x0307lightly backlogged\x0301"
        elif num < 350:  # < 70 subs
            return "is \x0304backlogged\x0301"
        elif num < 500:  # < 100 subs
            return "is \x02\x0304heavily backlogged\x0301\x0F"
        else:  # >= 100 subs
            return "is \x02\x1F\x0304severely backlogged\x0301\x0F"

    def get_aggregate_number(self, (subs, redirs, files)):
        """Returns an 'aggregate number' based on the real number of pending
        submissions in CAT:PEND (subs), open redirect submissions in WP:AFC/R
        (redirs), and open files-for-upload requests in WP:FFU (files)."""
        num = (subs * 5) + (redirs * 2) + (files * 2)
        return num
