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

import re

__all__ = ["RC"]

class RC(object):
    """A class to store data from an event received from our IRC watcher."""
    re_color = re.compile("\x03([0-9]{1,2}(,[0-9]{1,2})?)?")
    re_edit = re.compile("\A\[\[(.*?)\]\]\s(.*?)\s(http://.*?)\s\*\s(.*?)\s\*\s(.*?)\Z")
    re_log = re.compile("\A\[\[(.*?)\]\]\s(.*?)\s\*\s(.*?)\s\*\s(.*?)\Z")

    pretty_edit = "\x02New {0}\x0F: \x0314[[\x0307{1}\x0314]]\x0306 * \x0303{2}\x0306 * \x0302{3}\x0306 * \x0310{4}"
    pretty_log = "\x02New {0}\x0F: \x0303{1}\x0306 * \x0302{2}\x0306 * \x0310{3}"

    def __init__(self, chan, msg):
        self.chan = chan
        self.msg = msg

    def parse(self):
        """Parse a recent change event into some variables."""
        # Strip IRC color codes; we don't want or need 'em:
        self.msg = self.re_color.sub("", self.msg).strip()
        msg = self.msg
        self.is_edit = True

        # Flags: 'M' for minor edit, 'B' for bot edit, 'create' for a user
        # creation log entry, etc:
        try:
            page, self.flags, url, user, comment = self.re_edit.findall(msg)[0]
        except IndexError:
            # We're probably missing the http:// part, because it's a log
            # entry, which lacks a URL:
            page, flags, user, comment = self.re_log.findall(msg)[0]
            url = "http://{0}.org/wiki/{1}".format(self.chan, page)

            self.is_edit = False  # This is a log entry, not edit

            # Flags tends to have extra whitespace at the end when they're
            # log entries:
            self.flags = flags.strip()

        self.page, self.url, self.user, self.comment = page, url, user, comment

    def prettify(self):
        """Make a nice, colorful message to send back to the IRC front-end."""
        flags = self.flags
        # "New <event>:" if we don't know exactly what happened:
        event_type = flags
        if "N" in flags:
            event_type = "page"  # "New page:"
        elif flags == "delete":
            event_type = "deletion"  # "New deletion:"
        elif flags == "protect":
            event_type = "protection"  # "New protection:"
        elif flags == "create":
            event_type = "user"  # "New user:"
        if self.page == "Special:Log/move":
            event_type = "move"  # New move:
        else:
            event_type = "edit"  # "New edit:"
            if "B" in flags:
                # "New bot edit:"
                event_type = "bot " + event_type
            if "M" in flags:
                # "New minor edit:" OR "New minor bot edit:"
                event_type = "minor " + event_type

        if self.is_edit:
            return self.pretty_edit.format(event_type, self.page, self.user,
                                           self.url, self.comment)
        else:
            return self.pretty_log.format(event_type, self.user, self.url,
                                          self.comment)
