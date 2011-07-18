# -*- coding: utf-8  -*-

"""
Get information about an AFC submission by name.
"""

import json
import re
import urllib

from irc.classes import BaseCommand

class AFCReport(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Get information about an AFC submission by name."

    def check(self, data):
        if data.is_command and data.command in ["report", "afc_report"]:
            return True
        return False

    def process(self, data):
        self.data = data
        if not data.args:
            self.connection.reply(data, "what submission do you want me to give information about?")
            return

        pagename = ' '.join(data.args)
        pagename = pagename.replace("http://en.wikipedia.org/wiki/", "").replace("http://enwp.org/", "").replace("_", " ")
        pagename = pagename.strip()

        if page_exists(pagename):  # given '!report Foo', first try [[Foo]]
            self.report(pagename)
        else:  # if that doesn't work, try [[Wikipedia:Articles for creation/Foo]]
            if page_exists("Wikipedia:Articles for creation/" + pagename):
                self.report("Wikipedia:Articles for creation/" + pagename)
            else:  # if that doesn't work, try [[Wikipedia talk:Articles for creation/Foo]]
                if page_exists("Wikipedia talk:Articles for creation/" + pagename):
                    self.report("Wikipedia talk:Articles for creation/" + pagename)
                else:
                    self.connection.reply(data, "submission \x0302{0}\x0301 not found.".format(pagename))

    def report(self, pagename):
        data = self.data
        shortname = pagename.replace("Wikipedia:Articles for creation/", "").replace("Wikipedia talk:Articles for creation/", "")
        url = "http://enwp.org/" + urllib.quote(pagename.replace(" ", "_"))
        status = self.get_status(pagename)
        user, user_url = self.get_creator(pagename)

        self.connection.reply(data, "AfC submission report for \x0302{0}\x0301 ({1}):".format(shortname, url))
        self.connection.say(data.chan, "Status: \x0303{0}\x0301".format(status))
        if status == "accepted":  # the first edit will be the redirect [[WT:AFC/Foo]] -> [[Foo]], NOT the creation of the submission
            self.connection.say(data.chan, "Reviewed by \x0302{0}\x0301 ({1})".format(user, user_url))
        else:
            self.connection.say(data.chan, "Submitted by \x0302{0}\x0301 ({1})".format(user, user_url))

    def page_exists(self, pagename):
        params = {'action': 'query', 'format': 'json', 'titles': pagename}
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        try:
            res['query']['pages'].values()[0]['missing']  # this key will appear if the page does not exist
            return False
        except KeyError:  # if it's not there, the page exists
            return True

    def get_status(self, pagename):
        params = {'action': 'query', 'prop': 'revisions', 'rvprop':'content', 'rvlimit':'1', 'format': 'json'}
        params['titles'] = pagename
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        pageid = res['query']['pages'].keys()[0]
        content = res['query']['pages'][pageid]['revisions'][0]['*']
        lcontent = content.lower()
        if re.search("\{\{afc submission\|r\|(.*?)\}\}", lcontent):
            return "being reviewed"
        elif re.search("\{\{afc submission\|\|(.*?)\}\}", lcontent):
            return "pending"
        elif re.search("\{\{afc submission\|d\|(.*?)\}\}", lcontent):
            try:
                reason = re.findall("\{\{afc submission\|d\|(.*?)(\||\}\})", lcontent)[0][0]
                return "declined with reason \"{0}\"".format(reason)
            except IndexError:
                return "declined"
        else:
            if "#redirect" in content:
                return "accepted"
            else:
                return "unkown"

    def get_creator(self, pagename):
        params = {'action': 'query', 'prop': 'revisions', 'rvprop': 'user', 'rvdir': 'newer', 'rvlimit': '1', 'format': 'json'}
        params['titles'] = pagename
        data = urllib.urlencode(params)
        raw = urllib.urlopen("http://en.wikipedia.org/w/api.php", data).read()
        res = json.loads(raw)
        user = res['query']['pages'].values()[0]['revisions'][0]['user']
        user_url = "http://enwp.org/User_talk:" + urllib.quote(user.replace(" ", "_"))
        return user, user_url
