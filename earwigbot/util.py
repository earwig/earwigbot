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

import argparse
from os import path

from earwigbot import __version__
from earwigbot.bot import Bot

class BotUtility(object):
    """
    DOCSTRING NEEDED
    """

    def version(self):
        return __version__

    def run(self):
        root_dir = path.abspath(path.curdir())
        bot = Bot(root_dir)
        try:
            bot.run()
        finally:
            bot.stop()

    def main(self):
        print "EarwigBot v{0}\n".format(self.version())
        parser = argparse.ArgumentParser(description=BotUtility.__doc__)

        parser.add_argument("-V", "--version", action="version",
                            version=self.version())

        args = parser.parse_args()
#        args.func(args)


main = BotUtility().main

if __name__ == "__main__":
    main()
