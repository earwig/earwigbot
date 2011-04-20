# -*- coding: utf-8  -*-

# Report the status of AFC submissions, either as an automatic message on join or a request via !status.

import json
import re
import urllib

from config.irc_config import *
from irc.base_command import BaseCommand

class AFCStatus(BaseCommand):
    def get_hooks(self):
        return ["join", "msg"]

    def get_help(self, command):
        return "Get the number of pending AfC submissions, open redirect requests, and open file upload requests."

    def check(self, data):
        if data.is_command and (data.command == "status" or
        data.command == "count" or data.command == "num" or
        data.command == "number" or data.command == "afc_status"):
            return True
        if data.line[1] == "JOIN" and data.chan in AFC_CHANS:
            return True
        return False

    def process(self, data):
        if data.line[1] == "JOIN":
            notice = self.get_join_notice()
            self.connection.notice(data.nick, notice)
            return

        if data.args:
            if data.args[0].startswith("sub") or data.args[0] == "s":
                subs = self.count_submissions()
                self.connection.reply(data, "there are currently %s pending AfC submissions." % subs)

            elif data.args[0].startswith("redir") or data.args[0] == "r":
                redirs = self.count_redirects()
                self.connection.reply(data, "there are currently %s open redirect requests." % redirs)

            elif data.args[0].startswith("file") or data.args[0] == "f":
                files = self.count_redirects()
                self.connection.reply(data, "there are currently %s open file upload requests." % files)

            elif data.args[0].startswith("agg") or data.args[0] == "a":
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

            elif data.args[0].startswith("join") or data.args[0] == "j":
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
        params = {'action': 'query', 'list': 'categorymembers', 'cmlimit':'500', 'format': 'json'}
        params['cmtitle'] = "Category:Pending_AfC_submissions"
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        subs = len(res['query']['categorymembers'])
        subs -= 2 # remove [[Wikipedia:Articles for creation/Redirects]] and [[Wikipedia:Files for upload]], which aren't real submissions
        return subs

    def count_redirects(self):
        content = self.get_page("Wikipedia:Articles_for_creation/Redirects")
        total = len(re.findall("==\s*(Redirect|Category) request: \[\[(.*?)\]\]\s*==", content))
        closed = content.lower().count("{{afc-c|b}}")
        redirs = total - closed
        return redirs

    def count_files(self):
        content = self.get_page("Wikipedia:Files_for_upload")
        total = len(re.findall("^\s*==(.*?)==\s*$", content, re.MULTILINE))
        closed = content.lower().count("{{ifu-c|b}}")
        files = total - closed
        return files

    def get_page(self, pagename):
        params = {'action': 'query', 'prop': 'revisions', 'rvprop':'content', 'rvlimit':'1', 'format': 'json'}
        params['titles'] = pagename
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        pageid = res['query']['pages'].keys()[0]
        content = res['query']['pages'][pageid]['revisions'][0]['*']
        return content

    def get_aggregate(self, num):
        if num == 0:
            agg = "is \x02\x0303clear\x0301\x0F"
        elif num < 60:
            agg = "is \x0303almost clear\x0301"
        elif num < 125:
            agg = "has a \x0312small backlog\x0301"
        elif num < 175:
            agg = "has an \x0307average backlog\x0301"
        elif num < 250:
            agg = "is \x0304backlogged\x0301"
        elif num < 300:
            agg = "is \x02\x0304heavily backlogged\x0301\x0F"
        else:
            agg = "is \x02\x1F\x0304severely backlogged\x0301\x0F"
        return agg

    def get_aggregate_number(self, (subs, redirs, files)):
        num = (subs * 5) + (redirs * 2) + (files * 2)
        return num
