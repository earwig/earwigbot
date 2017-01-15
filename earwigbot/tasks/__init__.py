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

from earwigbot import exceptions
from earwigbot import wiki

__all__ = ["Task"]

class Task(object):
    """
    **EarwigBot: Base Bot Task**

    This package provides built-in wiki bot "tasks" EarwigBot runs. Additional
    tasks can be installed as plugins in the bot's working directory.

    This class (import with ``from earwigbot.tasks import Task``) can be
    subclassed to create custom bot tasks.

    To run a task, use :py:meth:`bot.tasks.start(name, **kwargs)
    <earwigbot.managers.TaskManager.start>`. ``**kwargs`` get passed to the
    Task's :meth:`run` method.
    """
    name = None
    number = 0

    def __init__(self, bot):
        """Constructor for new tasks.

        This is called once immediately after the task class is loaded by
        the task manager (in :py:meth:`tasks.load()
        <earwigbot.managers._ResourceManager.load>`). Don't override this
        directly; if you do, remember to place ``super(Task, self).__init()``
        first. Use :py:meth:`setup` for typical task-init/setup needs.
        """
        self.bot = bot
        self.config = bot.config
        self.logger = bot.tasks.logger.getChild(self.name)

        number = self.config.tasks.get(self.name, {}).get("number")
        if number is not None:
            self.number = number
        self.setup()

    def __repr__(self):
        """Return the canonical string representation of the Task."""
        res = "Task(name={0!r}, number={1!r}, bot={2!r})"
        return res.format(self.name, self.number, self.bot)

    def __str__(self):
        """Return a nice string representation of the Task."""
        res = "<Task {0} ({1}) of {2}>"
        return res.format(self.name, self.number, self.bot)

    def setup(self):
        """Hook called immediately after the task is loaded.

        Does nothing by default; feel free to override.
        """
        pass

    def run(self, **kwargs):
        """Main entry point to run a given task.

        This is called directly by :py:meth:`tasks.start()
        <earwigbot.managers.TaskManager.start>` and is the main way to make a
        task do stuff. *kwargs* will be any keyword arguments passed to
        :py:meth:`~earwigbot.managers.TaskManager.start`, which are entirely
        optional.
        """
        pass

    def unload(self):
        """Hook called immediately before the task is unloaded.

        Does nothing by default; feel free to override.
        """
        pass

    def make_summary(self, comment):
        """Make an edit summary by filling in variables in a config value.

        :py:attr:`config.wiki["summary"] <earwigbot.config.BotConfig.wiki>` is
        used, where ``$2`` is replaced by the main summary body, given by the
        *comment* argument, and ``$1`` is replaced by the task number.

        If the config value is not found, we'll just return *comment* as-is.
        """
        try:
            summary = self.bot.config.wiki["summary"]
        except KeyError:
            return comment
        return summary.replace("$1", str(self.number)).replace("$2", comment)

    def shutoff_enabled(self, site=None):
        """Return whether on-wiki shutoff is enabled for this task.

        We check a certain page for certain content. This is determined by
        our config file: :py:attr:`config.wiki["shutoff"]["page"]
        <earwigbot.config.BotConfig.wiki>` is used as the title, with any
        embedded ``$1`` replaced by our username and ``$2``  replaced by the
        task number; and :py:attr:`config.wiki["shutoff"]["disabled"]
        <earwigbot.config.BotConfig.wiki>` is used as the content.

        If the page has that exact content or the page does not exist, then
        shutoff is "disabled", meaning the bot is supposed to run normally, and
        we return  ``False``. If the page's content is something other than
        what we expect, shutoff is enabled, and we return ``True``.

        If a site is not provided, we'll try to use :py:attr:`self.site <site>`
        if it's set. Otherwise, we'll use our default site.
        """
        if not site:
            if hasattr(self, "site"):
                site = getattr(self, "site")
            else:
                site = self.bot.wiki.get_site()

        try:
            cfg = self.config.wiki["shutoff"]
        except KeyError:
            return False
        title = cfg.get("page", "User:$1/Shutoff/Task $2")
        username = site.get_user().name
        title = title.replace("$1", username).replace("$2", str(self.number))
        page = site.get_page(title)

        try:
            content = page.get()
        except exceptions.PageNotFoundError:
            return False
        if content == cfg.get("disabled", "run"):
            return False

        self.logger.warn("Emergency task shutoff has been enabled!")
        return True
