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
EarwigBot Runner

This is a very simple script that can be run from anywhere. It will add the
'earwigbot' package to sys.path if it's not already in there (i.e., it hasn't
been "installed"), accept a root_dir (the directory in which bot.py is located)
and a decryption key from raw_input (if passwords are encrypted), then call
config.load() and decrypt any passwords, and finally call the main() function
of earwigbot.main.
"""

from os import path
import sys

def run():
    pkg_dir = path.split(path.dirname(path.abspath(__file__)))[0]
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

    from earwigbot.config import config
    from earwigbot import main

    root_dir = raw_input()
    config_path = path.join(root_dir, "config.json")
    log_dir = path.join(root_dir, "logs")
    is_encrypted = config.load(config_path, log_dir)
    if is_encrypted:
        config._decryption_key = raw_input()
        config.decrypt(config.wiki, "password")
        config.decrypt(config.wiki, "search", "credentials", "key")
        config.decrypt(config.wiki, "search", "credentials", "secret")
        config.decrypt(config.irc, "frontend", "nickservPassword")
        config.decrypt(config.irc, "watcher", "nickservPassword")

    try:
        main.main()
    except KeyboardInterrupt:
        main.logger.critical("KeyboardInterrupt: stopping main bot loop")
        exit(1)

if __name__ == "__main__":
    run()
