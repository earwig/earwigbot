# -*- coding: utf-8  -*-

import threading
import time

from classes import BaseCommand

class Command(BaseCommand):
    """Set a message to be repeated to you in a certain amount of time."""
    name = "remind"

    def check(self, data):
        if data.is_command and data.command in ["remind", "reminder"]:
            return True
        return False

    def process(self, data):
        if not data.args:
            msg = "please specify a time (in seconds) and a message in the following format: !remind <time> <msg>."
            self.connection.reply(data, msg)
            return

        try:
            wait = int(data.args[0])
        except ValueError:
            msg = "the time must be given as an integer, in seconds."
            self.connection.reply(data, msg)
            return
        message = ' '.join(data.args[1:])
        if not message:
            msg = "what message do you want me to give you when time is up?"
            self.connection.reply(data, msg)
            return

        end = time.localtime(time.time() + wait)
        end_time = time.strftime("%b %d %H:%M:%S", end)
        end_time_with_timezone = time.strftime("%b %d %H:%M:%S %Z", end)

        msg = 'Set reminder for "{0}" in {1} seconds (ends {2}).'
        msg = msg.format(message, wait, end_time_with_timezone)
        self.connection.reply(data, msg)

        t_reminder = threading.Thread(target=self.reminder,
                                      args=(data, message, wait))
        t_reminder.name = "reminder " + end_time
        t_reminder.daemon = True
        t_reminder.start()

    def reminder(self, data, message, wait):
        time.sleep(wait)
        self.connection.reply(data, message)
