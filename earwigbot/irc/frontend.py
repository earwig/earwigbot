# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2016 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from time import sleep

from earwigbot.irc import IRCConnection, Data

__all__ = ["Frontend"]

class Frontend(IRCConnection):
    """
    **EarwigBot: IRC Frontend Component**

    The IRC frontend runs on a normal IRC server and expects users to interact
    with it and give it commands. Commands are stored as "command classes",
    subclasses of :py:class:`~earwigbot.commands.Command`. All command classes
    are automatically imported by :py:meth:`commands.load()
    <earwigbot.managers._ResourceManager.load>` if they are in
    :py:mod:`earwigbot.commands` or the bot's custom command directory
    (explained in the :doc:`documentation </customizing>`).
    """
    NICK_SERVICES = "NickServ"

    def __init__(self, bot):
        self.bot = bot
        cf = bot.config.irc["frontend"]
        base = super(Frontend, self)
        base.__init__(cf["host"], cf["port"], cf["nick"], cf["ident"],
                      cf["realname"], bot.logger.getChild("frontend"))

        self._auth_wait = False
        self._connect()

    def __repr__(self):
        """Return the canonical string representation of the Frontend."""
        res = "Frontend(host={0!r}, port={1!r}, nick={2!r}, ident={3!r}, realname={4!r}, bot={5!r})"
        return res.format(self.host, self.port, self.nick, self.ident,
                          self.realname, self.bot)

    def __str__(self):
        """Return a nice string representation of the Frontend."""
        res = "<Frontend {0}!{1} at {2}:{3}>"
        return res.format(self.nick, self.ident, self.host, self.port)

    def _join_channels(self):
        """Join all startup channels as specified by the config file."""
        for chan in self.bot.config.irc["frontend"]["channels"]:
            self.join(chan)

    def _process_message(self, line):
        """Process a single message from IRC."""
        if line[1] == "JOIN":
            data = Data(self.nick, line, msgtype="JOIN")
            self.bot.commands.call("join", data)

        elif line[1] == "PART":
            data = Data(self.nick, line, msgtype="PART")
            self.bot.commands.call("part", data)

        elif line[1] == "PRIVMSG":
            data = Data(self.nick, line, msgtype="PRIVMSG")
            if data.is_private:
                self.bot.commands.call("msg_private", data)
            else:
                self.bot.commands.call("msg_public", data)
            self.bot.commands.call("msg", data)

        elif line[1] == "NOTICE":
            data = Data(self.nick, line, msgtype="NOTICE")
            if self._auth_wait and data.nick == self.NICK_SERVICES:
                if data.msg.startswith("This nickname is registered."):
                    return
                self._auth_wait = False
                sleep(2)  # Wait for hostname change to propagate
                self._join_channels()

        elif line[1] == "376":  # On successful connection to the server
            # If we're supposed to auth to NickServ, do that:
            try:
                username = self.bot.config.irc["frontend"]["nickservUsername"]
                password = self.bot.config.irc["frontend"]["nickservPassword"]
            except KeyError:
                self._join_channels()
            else:
                self.logger.debug("Identifying with services")
                msg = "IDENTIFY {0} {1}".format(username, password)
                self.say(self.NICK_SERVICES, msg, hidelog=True)
                self._auth_wait = True

        elif line[1] == "401":  # No such nickname
            if self._auth_wait and line[3] == self.NICK_SERVICES:
                # Services is down, or something...?
                self._auth_wait = False
                self._join_channels()
