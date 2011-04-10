# -*- coding: utf-8  -*-

from subprocess import *

try:
    from config.secure_config import *
except ImportError:
    print "Can't find a secure_config file!"
    print "Make sure you have configured the bot by moving 'config/secure_config.py.default' to 'config/secure_config.py' and by filling out the information inside."
    exit()

while 1:
    cmd = ['python', 'bot.py']
    call(cmd)