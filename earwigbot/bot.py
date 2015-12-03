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

import logging
from threading import Lock, Thread, enumerate as enumerate_threads
from time import gmtime, sleep

from earwigbot import __version__
from earwigbot.config import BotConfig
from earwigbot.irc import Frontend, Watcher
from earwigbot.managers import CommandManager, TaskManager
from earwigbot.wiki import SitesDB

__all__ = ["Bot"]

class Bot(object):
    """
    **EarwigBot: Main Bot Class**

    The :py:class:`Bot` class is the core of EarwigBot, essentially responsible
    for starting the various bot components and making sure they are all happy.

    EarwigBot has three components that can run independently of each other: an
    IRC front-end, an IRC watcher, and a wiki scheduler.

    - The IRC front-end runs on a normal IRC server and expects users to
      interact with it/give it commands.
    - The IRC watcher runs on a wiki recent-changes server and listens for
      edits. Users cannot interact with this part of the bot.
    - The wiki scheduler runs wiki-editing bot tasks in separate threads at
      user-defined times through a cron-like interface.

    The :py:class:`Bot` object is accessible from within commands and tasks as
    :py:attr:`self.bot`. This is the primary way to access data from other
    components of the bot. For example, our
    :py:class:`~earwigbot.config.BotConfig` object is accessable from
    :py:attr:`bot.config`, tasks can be started with
    :py:meth:`bot.tasks.start() <earwigbot.managers.TaskManager.start>`, and
    sites can be loaded from the wiki toolset with
    :py:meth:`bot.wiki.get_site() <earwigbot.wiki.sitesdb.SitesDB.get_site>`.
    """

    def __init__(self, root_dir, level=logging.INFO):
        self.config = BotConfig(self, root_dir, level)
        self.logger = logging.getLogger("earwigbot")
        self.commands = CommandManager(self)
        self.tasks = TaskManager(self)
        self.wiki = SitesDB(self)
        self.frontend = None
        self.watcher = None

        self.component_lock = Lock()
        self._keep_looping = True

        self.config.load()
        self.commands.load()
        self.tasks.load()

    def __repr__(self):
        """Return the canonical string representation of the Bot."""
        return "Bot(config={0!r})".format(self.config)

    def __str__(self):
        """Return a nice string representation of the Bot."""
        return "<Bot at {0}>".format(self.config.root_dir)

    def _dispatch_irc_component(self, name, klass):
        """Create a new IRC component, record it internally, and start it."""
        component = klass(self)
        setattr(self, name, component)
        Thread(name="irc_" + name, target=component.loop).start()

    def _start_irc_components(self):
        """Start the IRC frontend/watcher in separate threads if enabled."""
        if self.config.components.get("irc_frontend"):
            self.logger.info("Starting IRC frontend")
            self._dispatch_irc_component("frontend", Frontend)
        if self.config.components.get("irc_watcher"):
            self.logger.info("Starting IRC watcher")
            self._dispatch_irc_component("watcher", Watcher)

    def _start_wiki_scheduler(self):
        """Start the wiki scheduler in a separate thread if enabled."""
        def wiki_scheduler():
            run_at = 15
            while self._keep_looping:
                self.tasks.schedule()
                sleep(60 + run_at - gmtime().tm_sec)

        if self.config.components.get("wiki_scheduler"):
            self.logger.info("Starting wiki scheduler")
            thread = Thread(name="wiki_scheduler", target=wiki_scheduler)
            thread.daemon = True  # Stop if other threads stop
            thread.start()

    def _keep_irc_component_alive(self, name, klass):
        """Ensure that IRC components stay connected, else restart them."""
        component = getattr(self, name)
        if component:
            component.keep_alive()
            if component.is_stopped():
                log = "IRC {0} has stopped; restarting".format(name)
                self.logger.warn(log)
                self._dispatch_irc_component(name, klass)

    def _stop_irc_components(self, msg):
        """Request the IRC frontend and watcher to stop if enabled."""
        if self.frontend:
            self.frontend.stop(msg)
        if self.watcher:
            self.watcher.stop(msg)

    def _stop_daemon_threads(self):
        """Notify the user of which threads are going to be killed.

        Unfortunately, there is no method right now of stopping command and
        task threads safely. This is because there is no way to tell them to
        stop like the IRC components can be told; furthermore, they are run as
        daemons, and daemon threads automatically stop without calling any
        __exit__ or try/finally code when all non-daemon threads stop. They
        were originally implemented as regular non-daemon threads, but this
        meant there was no way to completely stop the bot if tasks were
        running, because all other threads would exit and threading would
        absorb KeyboardInterrupts.

        The advantage of this is that stopping the bot is truly guarenteed to
        *stop* the bot, while the disadvantage is that the threads are given no
        advance warning of their forced shutdown.
        """
        tasks = []
        component_names = self.config.components.keys()
        skips = component_names + ["MainThread", "reminder", "irc:quit"]
        for thread in enumerate_threads():
            if thread.is_alive() and not any(
                    thread.name.startswith(skip) for skip in skips):
                tasks.append(thread.name)
        if tasks:
            log = "The following commands or tasks will be killed: {0}"
            self.logger.warn(log.format(", ".join(tasks)))

    @property
    def is_running(self):
        """Whether or not the bot is currently running.

        This may return ``False`` even if the bot is still technically active,
        but in the process of shutting down.
        """
        return self._keep_looping

    def run(self):
        """Main entry point into running the bot.

        Starts all config-enabled components and then enters an idle loop,
        ensuring that all components remain online and restarting components
        that get disconnected from their servers.
        """
        self.logger.info("Starting bot (EarwigBot {0})".format(__version__))
        self._start_irc_components()
        self._start_wiki_scheduler()
        while self._keep_looping:
            with self.component_lock:
                self._keep_irc_component_alive("frontend", Frontend)
                self._keep_irc_component_alive("watcher", Watcher)
            sleep(2)

    def restart(self, msg=None):
        """Reload config, commands, tasks, and safely restart IRC components.

        This is thread-safe, and it will gracefully stop IRC components before
        reloading anything. Note that you can safely reload commands or tasks
        without restarting the bot with :py:meth:`bot.commands.load()
        <earwigbot.managers._ResourceManager.load>` or
        :py:meth:`bot.tasks.load() <earwigbot.managers._ResourceManager.load>`.
        These should not interfere with running components or tasks.

        If given, *msg* will be used as our quit message.
        """
        if msg:
            self.logger.info('Restarting bot ("{0}")'.format(msg))
        else:
            self.logger.info("Restarting bot")
        with self.component_lock:
            self._stop_irc_components(msg)
            self.config.load()
            self.commands.load()
            self.tasks.load()
            self._start_irc_components()

    def stop(self, msg=None):
        """Gracefully stop all bot components.

        If given, *msg* will be used as our quit message.
        """
        if msg:
            self.logger.info('Stopping bot ("{0}")'.format(msg))
        else:
            self.logger.info("Stopping bot")
        with self.component_lock:
            self._stop_irc_components(msg)
        self._keep_looping = False
        self._stop_daemon_threads()
