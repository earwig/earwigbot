# -*- coding: utf-8  -*-

# A class to store data on an individual event received from our IRC watcher.

import re

class RC(object):
    def __init__(self, msg):
        """store data on an individual event received from our IRC watcher"""
        self.msg = msg

    def parse(self):
        """parse recent changes log into some variables"""
        msg = self.msg
        msg = re.sub("\x03([0-9]{1,2}(,[0-9]{1,2})?)?", "", msg) # strip IRC color codes; we don't want/need 'em
        msg = msg.strip()
        self.msg = msg
        self.is_edit = True

        # flags: 'M' for minor edit, 'B' for bot edit, 'create' for a user creation log entry...
        try:
            page, flags, url, user, comment = re.findall("\A\[\[(.*?)\]\]\s(.*?)\s(http://.*?)\s\*\s(.*?)\s\*\s(.*?)\Z", msg)[0] 
        except IndexError: # we're probably missing the http:// part, because it's a log entry, which lacks a url
            page, flags, user, comment = re.findall("\A\[\[(.*?)\]\]\s(.*?)\s\*\s(.*?)\s\*\s(.*?)\Z", msg)[0]
            url = "http://en.wikipedia.org/wiki/{}".format(page)
            flags = flags.strip() # flag tends to have a extraneous whitespace character at the end when it's a log entry
            self.is_edit = False # this is a log entry, not edit
        
        self.page, self.flags, self.url, self.user, self.comment = page, flags, url, user, comment

    def get_pretty(self):
        """make a nice, colorful message from self.msg to send to the front-end"""
        flags = self.flags
        event_type = flags # "New <event>:" if we don't know exactly what happened
        if "N" in flags:
            event_type = "page" # "New page:"
        elif flags == "delete":
            event_type = "deletion" # "New deletion:"
        elif flags == "protect":
            event_type = "protection" # "New protection:"
        elif flags == "create":
            event_type = "user" # "New user:"
        else:
            event_type = "edit" # "New edit:"
            if "B" in flags:
                event_type = "bot {}".format(event_type) # "New bot edit:"
            if "M" in flags:
                event_type = "minor {}".format(event_type) # "New minor edit:" OR "New minor bot edit:"
        
        if self.is_edit:
            pretty = "\x02New {0}\x0F: \x0314[[\x0307{1}\x0314]]\x0306 *\x0303 {2}\x0306 *\x0302 {3}\x0306 *\x0310 {4}".format(event_type, self.page, self.user, self.url, self.comment)
        else:
            pretty = "\x02New {0}\x0F: \x0303{1}\x0306 *\x0302 {2}\x0306 *\x0310 {3}".format(event_type, self.user, self.url, self.comment)
        
        return pretty
