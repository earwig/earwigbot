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

from earwigbot.commands import Command

class ChanOps(Command):
    """Voice, devoice, op, or deop users in the channel, or join or part from
    other channels."""
    name = "chanops"
    commands = ["chanops", "voice", "devoice", "op", "deop", "join", "part"]

    def process(self, data):
        if data.command == "chanops":
            msg = "Available commands are !voice, !devoice, !op, !deop, !join, and !part."
            self.reply(data, msg)
            return
        de_escalate = data.command in ["devoice", "deop"]
        if de_escalate and (not data.args or data.args[0] == data.nick):
            target = data.nick
        elif not self.config.irc["permissions"].is_admin(data):
            self.reply(data, "You must be a bot admin to use this command.")
            return

        if data.command == "join":
            self.do_join(data)
        elif data.command == "part":
            self.do_part(data)
        else:
            # If it is just !op/!devoice/whatever without arguments, assume
            # they want to do this to themselves:
            if not data.args:
                target = data.nick
            else:
                target = data.args[0]
            command = data.command.upper()
            self.say("ChanServ", " ".join((command, data.chan, target)))
            log = "{0} requested {1} on {2} in {3}"
            self.logger.info(log.format(data.nick, command, target, data.chan))

    def do_join(self, data):
        if data.args:
            channel = data.args[0]
            if not channel.startswith("#"):
                channel = "#" + channel
        else:
            msg = "You must specify a channel to join or part from."
            self.reply(data, msg)
            return

        self.join(channel)
        log = "{0} requested JOIN to {1}".format(data.nick, channel)
        self.logger.info(log)

    def do_part(self, data):
        channel = data.chan
        reason = None
        if data.args:
            if data.args[0].startswith("#"):
                # "!part #channel reason for parting"
                channel = data.args[0]
                if data.args[1:]:
                    reason = " ".join(data.args[1:])
            else:  # "!part reason for parting"; assume current channel
                reason = " ".join(data.args)

        msg = "Requested by {0}".format(data.nick)
        log = "{0} requested PART from {1}".format(data.nick, channel)
        if reason:
            msg += ": {0}".format(reason)
            log += ' ("{0}")'.format(reason)
        self.part(channel, msg)
        self.logger.info(log)
