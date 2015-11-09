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

__all__ = ["BotFormatter"]

class BotFormatter(logging.Formatter):
    def __init__(self, color=False):
        self._format = super(BotFormatter, self).format
        if color:
            fmt = "[%(asctime)s %(lvl)s] %(name)s: %(message)s"
            self.format = lambda rec: self._format(self.format_color(rec))
        else:
            fmt = "[%(asctime)s %(levelname)-8s] %(name)s: %(message)s"
            self.format = self._format
        datefmt = "%Y-%m-%d %H:%M:%S"
        super(BotFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def format_color(self, record):
        l = record.levelname.ljust(8)
        if record.levelno == logging.DEBUG:
            record.lvl = l.join(("\x1b[34m", "\x1b[0m"))  # Blue
        if record.levelno == logging.INFO:
            record.lvl = l.join(("\x1b[32m", "\x1b[0m"))  # Green
        if record.levelno == logging.WARNING:
            record.lvl = l.join(("\x1b[33m", "\x1b[0m"))  # Yellow
        if record.levelno == logging.ERROR:
            record.lvl = l.join(("\x1b[31m", "\x1b[0m"))  # Red
        if record.levelno == logging.CRITICAL:
            record.lvl = l.join(("\x1b[1m\x1b[31m", "\x1b[0m"))  # Bold red
        return record
