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

import logging

from earwigbot.irc import IRCConnection, RC, BrokenSocketException
from earwigbot.config import config

__all__ = ["Watcher"]

class Watcher(IRCConnection):
    """
    EarwigBot's IRC Watcher Component

    The IRC watcher runs on a wiki recent-changes server and listens for
    edits. Users cannot interact with this part of the bot. When an event
    occurs, we run it through some rules stored in our config, which can result
    in wiki bot tasks being started (located in tasks/) or messages being sent
    to channels on the IRC frontend.
    """

    def __init__(self, frontend=None):
        self.logger = logging.getLogger("earwigbot.watcher")
        cf = config.irc["watcher"]
        base = super(Watcher, self)
        base.__init__(cf["host"], cf["port"], cf["nick"], cf["ident"],
                      cf["realname"], self.logger)
        self.frontend = frontend
        self._prepare_process_hook()
        self._connect()

    def _process_message(self, line):
        """Process a single message from IRC."""
        line = line.strip().split()

        if line[1] == "PRIVMSG":
            chan = line[2]

            # Ignore messages originating from channels not in our list, to
            # prevent someone PMing us false data:
            if chan not in config.irc["watcher"]["channels"]:
                return

            msg = " ".join(line[3:])[1:]
            rc = RC(msg)  # New RC object to store this event's data
            rc.parse()  # Parse a message into pagenames, usernames, etc.
            self._process_rc_event(rc)

        # If we are pinged, pong back:
        elif line[0] == "PING":
            self.pong(line[1])

        # When we've finished starting up, join all watcher channels:
        elif line[1] == "376":
            for chan in config.irc["watcher"]["channels"]:
                self.join(chan)

    def _prepare_process_hook(self):
        """Create our RC event process hook from information in config.

        This will get put in the function self._process_hook, which takes an RC
        object and returns a list of frontend channels to report this event to.
        """
        # Default RC process hook does nothing:
        self._process_hook = lambda rc: ()
        try:
            rules = config.data["rules"]
        except KeyError:
            return
        try:
            module = compile(rules, config.config_path, "exec")
        except Exception:
            e = "Could not compile config file's RC event rules"
            self.logger.exception(e)
            return
        try:
            self._process_hook = module.process
        except AttributeError:
            e = "RC event rules compiled correctly, but no process(rc) function was found"
            self.logger.error(e)
            return

    def _process_rc_event(self, rc):
        """Process a recent change event from IRC (or, an RC object).

        The actual processing is configurable, so we don't have that hard-coded
        here. We simply call our process hook (self._process_hook), created by
        self._prepare_process_hook() from information in the "rules" section of
        our config.
        """
        chans = self._process_hook(rc)
        if chans and self.frontend:
            pretty = rc.prettify()
            for chan in chans:
                self.frontend.say(chan, pretty)
