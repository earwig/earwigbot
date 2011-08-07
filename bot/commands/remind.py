# -*- coding: utf-8  -*-

"""
Set a message to be repeated to you in a certain amount of time.
"""

import threading
import time

from irc.classes import BaseCommand

class Remind(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Set a message to be repeated to you in a certain amount of time."

    def check(self, data):
        if data.is_command and data.command in ["remind", "reminder"]:
            return True
        return False

    def process(self, data):
        if not data.args:
            self.connection.reply(data, "please specify a time (in seconds) and a message in the following format: !remind <time> <msg>.")
            return

        try:
            wait = int(data.args[0])
        except ValueError:
            self.connection.reply(data, "the time must be given as an integer, in seconds.")
            return
        message = ' '.join(data.args[1:])
        if not message:
            self.connection.reply(data, "what message do you want me to give you when time is up?")
            return

        end_time = time.strftime("%b %d %H:%M:%S", time.localtime(time.time() + wait))
        end_time_with_timezone = time.strftime("%b %d %H:%M:%S %Z", time.localtime(time.time() + wait))
        self.connection.reply(data, 'Set reminder for "{0}" in {1} seconds (ends {2}).'.format(message, wait, end_time_with_timezone))

        t_reminder = threading.Thread(target=self.reminder, args=(data, message, wait))
        t_reminder.name = "reminder " + end_time
        t_reminder.daemon = True
        t_reminder.start()

    def reminder(self, data, message, wait):
        time.sleep(wait)
        self.connection.reply(data, message)
