# -*- coding: utf-8  -*-

# A class to store data on an individual event received from our IRC watcher.

import re

class RC:
    def __init__(self, msg):
        """store data on an individual event received from our IRC watcher"""
        self.msg = msg

    def parse(self):
        """parse recent changes log into some variables"""
        msg = self.msg
        msg = re.sub("\x03([0-9]{1,2}(,[0-9]{1,2})?)?", "", msg) # strip IRC color codes; we don't want/need 'em
        msg = msg.strip()
        self.msg = msg

        # page name of the modified page
        # 'M' for minor edit, 'B' for bot edit, 'create' for a user creation log entry...
        try:
            page, flags, url, user, comment = re.findall("\A\[\[(.*?)\]\]\s(.*?)\s(http://.*?)\s\*\s(.*?)\s\*\s(.*?)\Z", msg)[0] 
        except IndexError: # we're probably missing the http:// part, because it's a log entry, which lacks a url
            page, flags, user, comment = re.findall("\A\[\[(.*?)\]\]\s(.*?)\s\*\s(.*?)\s\*\s(.*?)\Z", msg)[0]
            url = "http://en.wikipedia.org/wiki/%s" % page
            flags = flags.strip() # flag tends to have a extraneous whitespace character at the end when it's a log entry
        
        self.page, self.flags, self.url, self.user, self.comment = page, flags, url, user, comment

    def pretty(self):
        """make a nice, colorful message from self.msg to send to the front-end"""
        pretty = self.msg
        return pretty
