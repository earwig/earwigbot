#! /usr/bin/env python
# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
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
EarwigBot

This is a thin wrapper for EarwigBot's main bot code, specified by bot_script.
The wrapper will automatically restart the bot when it shuts down (from
!restart, for example). It requests the bot's password at startup and reuses it
every time the bot restarts internally, so you do not need to re-enter the
password after using !restart.

For information about the bot as a whole, see the attached README.md file (in
markdown format!), the docs/ directory, and the LICENSE file for licensing
information. EarwigBot is released under the MIT license.
"""
from getpass import getpass
from subprocess import Popen, PIPE
from os import path
from sys import executable
from time import sleep

import earwigbot

bot_script = path.join(earwigbot.__path__[0], "runner.py")

def main():
    print "EarwigBot v{0}\n".format(earwigbot.__version__)

    is_encrypted = earwigbot.config.config.load()
    if is_encrypted:  # Passwords in the config file are encrypted
        key = getpass("Enter key to unencrypt bot passwords: ")
    else:
        key = None

    while 1:
        bot = Popen([executable, bot_script], stdin=PIPE)
        print >> bot.stdin, path.dirname(path.abspath(__file__))
        if is_encrypted:
            print >> bot.stdin, key
        return_code = bot.wait()
        if return_code == 1:
            exit()  # Let critical exceptions in the subprocess cause us to
                    # exit as well
        else:
            sleep(5)  # Sleep between bot runs following a non-critical
                      # subprocess exit

if __name__ == "__main__":
    main()
