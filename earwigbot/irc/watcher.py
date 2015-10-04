# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

import imp

from earwigbot.irc import IRCConnection, RC

__all__ = ["Watcher"]

class Watcher(IRCConnection):
    """
    **EarwigBot: IRC Watcher Component**

    The IRC watcher runs on a wiki recent-changes server and listens for
    edits. Users cannot interact with this part of the bot. When an event
    occurs, we run it through some rules stored in our working directory under
    :file:`rules.py`, which can result in wiki bot tasks being started or
    messages being sent to channels on the IRC frontend.
    """

    def __init__(self, bot):
        self.bot = bot
        cf = bot.config.irc["watcher"]
        base = super(Watcher, self)
        base.__init__(cf["host"], cf["port"], cf["nick"], cf["ident"],
                      cf["realname"], bot.logger.getChild("watcher"))
        self._prepare_process_hook()
        self._connect()

    def __repr__(self):
        """Return the canonical string representation of the Watcher."""
        res = "Watcher(host={0!r}, port={1!r}, nick={2!r}, ident={3!r}, realname={4!r}, bot={5!r})"
        return res.format(self.host, self.port, self.nick, self.ident,
                          self.realname, self.bot)

    def __str__(self):
        """Return a nice string representation of the Watcher."""
        res = "<Watcher {0}!{1} at {2}:{3}>"
        return res.format(self.nick, self.ident, self.host, self.port)

    def _process_message(self, line):
        """Process a single message from IRC."""
        if line[1] == "PRIVMSG":
            chan = line[2]

            # Ignore messages originating from channels not in our list, to
            # prevent someone PMing us false data:
            if chan not in self.bot.config.irc["watcher"]["channels"]:
                return

            msg = " ".join(line[3:])[1:]
            rc = RC(chan, msg)  # New RC object to store this event's data
            rc.parse()  # Parse a message into pagenames, usernames, etc.
            self._process_rc_event(rc)
            self.bot.commands.call("rc", rc)

        # When we've finished starting up, join all watcher channels:
        elif line[1] == "376":
            for chan in self.bot.config.irc["watcher"]["channels"]:
                self.join(chan)

    def _prepare_process_hook(self):
        """Create our RC event process hook from information in rules.py.

        This will get put in the function self._process_hook, which takes the
        Bot object and an RC object and returns a list of frontend channels to
        report this event to.
        """
        # Set a default RC process hook that does nothing:
        self._process_hook = lambda bot, rc: ()

        path = self.bot.config.root_dir
        try:
            f, path, desc = imp.find_module("rules", [path])
        except ImportError:
            return
        try:
            module = imp.load_module("rules", f, path, desc)
        except Exception:
            return
        finally:
            f.close()

        self._process_hook_module = module
        try:
            self._process_hook = module.process
        except AttributeError:
            e = "RC event rules imported correctly, but no process(bot, rc) function was found"
            self.logger.error(e)
            return

    def _process_rc_event(self, rc):
        """Process a recent change event from IRC (or, an RC object).

        The actual processing is configurable, so we don't have that hard-coded
        here. We simply call our process hook (self._process_hook), created by
        self._prepare_process_hook() from information in the "rules" section of
        our config.
        """
        chans = self._process_hook(self.bot, rc)
        with self.bot.component_lock:
            frontend = self.bot.frontend
            if chans and frontend and not frontend.is_stopped():
                pretty = rc.prettify()
                if len(pretty) > 400:
                    msg = pretty[:397] + "..."
                else:
                    msg = pretty[:400]
                for chan in chans:
                    frontend.say(chan, msg)
