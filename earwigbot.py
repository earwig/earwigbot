# -*- coding: utf-8  -*-

import time
from subprocess import *

try:
    from config import irc_config, secure_config
except ImportError:
    print """Missing a config file! Make sure you have configured the bot. All *.py.default files in config/
should have their .default extension removed, and the info inside should be corrected."""
    exit()

while 1:
    call(['python', 'core/main.py'])
    time.sleep(5) # sleep for five seconds between bot runs
