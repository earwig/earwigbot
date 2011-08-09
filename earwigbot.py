#! /usr/bin/env python
# -*- coding: utf-8  -*-

"""
EarwigBot

A thin wrapper for EarwigBot's main bot code, specified by bot_script. This
wrapper will automatically restart the bot when it shuts down (from !restart,
for example). It requests the bot's password at startup and reuses it every
time the bot restarts internally, so you do not need to re-enter the password
after using !restart.

For information about the bot as a whole, see the attached README.md file (in
markdown format!) and the LICENSE for licensing information.
"""

from getpass import getpass
from subprocess import Popen, PIPE
from os import path
from sys import executable
from time import sleep

from bot import config

__author__ = "Ben Kurtovic"
__copyright__ = "Copyright (C) 2009, 2010, 2011 by Ben Kurtovic"
__license__ = "MIT License"
__version__ = "0.1-dev"
__email__ = "ben.kurtovic@verizon.net"

bot_script = path.join(path.dirname(path.abspath(__file__)), "bot", "main.py")

def main():
    print "EarwigBot v{0}\n".format(__version__)

    is_encrypted = config.verify_config()
    if is_encrypted:  # passwords in the config file are encrypted
        key = getpass("Enter key to unencrypt bot passwords: ")
    else:
        key = None

    while 1:
        bot = Popen([executable, bot_script], stdin=PIPE)
        bot.communicate(key)  # give the key to core.config.load_config()
        return_code = bot.wait()
        if return_code == 1:
            exit()  # let critical exceptions in the subprocess cause us to
                    # exit as well
        else:
            sleep(5)  # sleep between bot runs following a non-critical
                      # subprocess exit

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "\nKeyboardInterrupt: stopping bot wrapper."
