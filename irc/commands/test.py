# -*- coding: utf-8  -*-

# A simple command to test the bot.

import random

actions, data = None, None

def call(a, d):
    global actions, data
    actions, data = a, d

    choices = ("say_hi()", "say_sup()")
    exec random.choice(choices)

def say_hi():
    actions.say(data.chan, "Hey \x02%s\x0F!" % data.nick)

def say_sup():
    actions.say(data.chan, "'sup \x02%s\x0F?" % data.nick)
