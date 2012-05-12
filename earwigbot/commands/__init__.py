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

__all__ = ["BaseCommand"]

class BaseCommand(object):
    """
    **EarwigBot: Base IRC Command**

    This package provides built-in IRC "commands" used by the bot's front-end
    component. Additional commands can be installed as plugins in the bot's
    working directory.

    This class (import with ``from earwigbot.commands import BaseCommand``),
    can be subclassed to create custom IRC commands.

    This docstring is reported to the user when they type ``"!help
    <command>"``.
    """
    # This is the command's name, as reported to the user when they use !help:
    name = None

    # Hooks are "msg", "msg_private", "msg_public", and "join". "msg" is the
    # default behavior; if you wish to override that, change the value in your
    # command subclass:
    hooks = ["msg"]

    def __init__(self, bot):
        """Constructor for new commands.

        This is called once when the command is loaded (from
        :py:meth:`commands.load() <earwigbot.managers._ResourceManager.load>`).
        *bot* is out base :py:class:`~earwigbot.bot.Bot` object. Generally you
        shouldn't need to override this; if you do, call
        ``super(Command, self).__init__()`` first.
        """
        self.bot = bot
        self.config = bot.config
        self.logger = bot.commands.logger.getChild(self.name)

        # Convenience functions:
        self.say = lambda target, msg: self.bot.frontend.say(target, msg)
        self.reply = lambda data, msg: self.bot.frontend.reply(data, msg)
        self.action = lambda target, msg: self.bot.frontend.action(target, msg)
        self.notice = lambda target, msg: self.bot.frontend.notice(target, msg)
        self.join = lambda chan: self.bot.frontend.join(chan)
        self.part = lambda chan, msg=None: self.bot.frontend.part(chan, msg)
        self.mode = lambda t, level, msg: self.bot.frontend.mode(t, level, msg)
        self.pong = lambda target: self.bot.frontend.pong(target)

    def check(self, data):
        """Return whether this command should be called in response to *data*.

        Given a :py:class:`~earwigbot.irc.data.Data` instance, return ``True``
        if we should respond to this activity, or ``False`` if we should ignore
        it and move on. Be aware that since this is called for each message
        sent on IRC, it should be cheap to execute and unlikely to throw
        exceptions.

        Most commands return ``True`` if :py:attr:`data.command
        <earwigbot.irc.data.Data.command>` ``==`` :py:attr:`self.name <name>`,
        otherwise they return ``False``. This is the default behavior of
        :py:meth:`check`; you need only override it if you wish to change that.
        """
        return data.is_command and data.command == self.name

    def process(self, data):
        """Main entry point for doing a command.

        Handle an activity (usually a message) on IRC. At this point, thanks
        to :py:meth:`check` which is called automatically by the command
        handler, we know this is something we should respond to. Place your
        command's body here.
        """
        pass
