#! /usr/bin/env python
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

"""
usage: :command:`earwigbot [-h] [-v] [-d] [-q] [-t NAME] [PATH]`

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
"""

from argparse import ArgumentParser
import logging
from os import path
from time import sleep

from earwigbot import __version__
from earwigbot.bot import Bot

__all__ = ["main"]

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
    parser.add_argument("-d", "--debug", action="store_true",
                        help="print all logs, including DEBUG-level messages")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="don't print any logs except warnings and errors")
    parser.add_argument("-t", "--task", metavar="NAME",
                        help="""given the name of a task, the bot will run it
                                instead of the main bot and then exit""")
    args = parser.parse_args()

    level = logging.INFO
    if args.debug and args.quiet:
        parser.print_usage()
        print "earwigbot: error: cannot show debug messages and be quiet at the same time"
        return
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    print version
    print

    bot = Bot(path.abspath(args.path), level=level)
    if args.task:
        thread = bot.tasks.start(args.task)
        if not thread:
            return
        try:
            while thread.is_alive():  # Keep it alive; it's a daemon
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            if thread.is_alive():
                bot.tasks.logger.warn("The task is will be killed")
    else:
        try:
            bot.run()
        except KeyboardInterrupt:
            pass
        finally:
            if bot._keep_looping:  # Indicates bot hasn't already been stopped
                bot.stop()

if __name__ == "__main__":
    main()
