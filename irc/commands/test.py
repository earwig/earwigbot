# -*- coding: utf-8  -*-

"""Test the bot!"""

import random

connection, data = None, None

def call(c, d):
    global connection, data
    connection, data = c, d

    choices = ("say_hi()", "say_sup()")
    exec random.choice(choices)

def say_hi():
    connection.say(data.chan, "Hey \x02%s\x0F!" % data.nick)

def say_sup():
    connection.say(data.chan, "'sup \x02%s\x0F?" % data.nick)
