#! /usr/bin/env python
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

"""
usage: :command:`earwigbot [-h] [-v] [-d | -q] [-t NAME] [PATH] ...`

This is EarwigBot's command-line utility, enabling you to easily start the bot
or run specific tasks.

.. glossary::

``PATH``
    path to the bot's working directory, which will be created if it doesn't
    exist; current directory assumed if not specified
``-h``, ``--help``
    show this help message and exit
``-v``, ``--version``
    show program's version number and exit
``-d``, ``--debug``
    print all logs, including ``DEBUG``-level messages
``-q``, ``--quiet``
    don't print any logs except warnings and errors
``-t NAME``, ``--task NAME``
    given the name of a task, the bot will run it instead of the main bot and
    then exit
``TASK_ARGS``
    with --task, will pass any remaining arguments to the task's
    :py:meth:`.Task.run` method

"""

from argparse import Action, ArgumentParser, REMAINDER
import logging
from os import path
from time import sleep

from earwigbot import __version__
from earwigbot.bot import Bot

__all__ = ["main"]

class _StoreTaskArg(Action):
    """A custom argparse action to read remaining command-line arguments."""
    def __call__(self, parser, namespace, values, option_string=None):
        kwargs = {}
        name = None
        for value in values:
            if value.startswith("-") and "=" in value:
                key, value = value.split("=", 1)
                self.insert(kwargs, key.lstrip("-"), value)
            elif name:
                if value.startswith("-"):
                    if name not in kwargs:
                        kwargs[name] = True
                    name = value.lstrip("-")
                else:
                    self.insert(kwargs, name, value)
                    name = None
            else:
                if value.startswith("-"):
                    name = value.lstrip("-")
        if name and name not in kwargs:
            kwargs[name] = True
        namespace.task_args = kwargs

    def insert(self, kwargs, key, value):
        """Add a key/value pair to kwargs; support multiple values per key."""
        if key in kwargs:
            try:
                kwargs[key].append(value)
            except AttributeError:
                kwargs[key] = [kwargs[key], value]
        else:
            kwargs[key] = value


def main():
    """Main entry point for the command-line utility."""
    version = "EarwigBot v{0}".format(__version__)
    desc = """This is EarwigBot's command-line utility, enabling you to easily
              start the bot or run specific tasks."""
    parser = ArgumentParser(description=desc)
    parser.add_argument("path", nargs="?", metavar="PATH", default=path.curdir,
                        help="""path to the bot's working directory, which will
                                be created if it doesn't exist; current
                                directory assumed if not specified""")
    parser.add_argument("-v", "--version", action="version", version=version)
    logger = parser.add_mutually_exclusive_group()
    logger.add_argument("-d", "--debug", action="store_true",
                        help="print all logs, including DEBUG-level messages")
    logger.add_argument("-q", "--quiet", action="store_true",
                        help="don't print any logs except warnings and errors")
    parser.add_argument("-t", "--task", metavar="NAME",
                        help="""given the name of a task, the bot will run it
                                instead of the main bot and then exit""")
    parser.add_argument("task_args", nargs=REMAINDER, action=_StoreTaskArg,
                        metavar="TASK_ARGS",
                        help="""with --task, will pass these arguments to the
                                task's run() method""")
    args = parser.parse_args()

    if not args.task and args.task_args:
        unrecognized = " ".join(args.task_args)
        parser.error("unrecognized arguments: {0}".format(unrecognized))

    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    print version
    print

    bot = Bot(path.abspath(args.path), level=level)
    if args.task:
        thread = bot.tasks.start(args.task, **args.task_args)
        if not thread:
            return
        try:
            while thread.is_alive():  # Keep it alive; it's a daemon
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if thread.is_alive():
                bot.tasks.logger.warn("The task will be killed")
    else:
        try:
            bot.run()
        except KeyboardInterrupt:
            pass
        finally:
            if bot.is_running:
                bot.stop()

if __name__ == "__main__":
    main()
