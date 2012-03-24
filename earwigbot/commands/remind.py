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

import threading
import time

from earwigbot.commands import BaseCommand

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
