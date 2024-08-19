# Copyright (C) 2009-2024 Ben Kurtovic <ben.kurtovic@gmail.com>
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

import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from earwigbot.commands import Command
from earwigbot.irc import Data


class Time(Command):
    """Report the current time in any timezone (UTC default), UNIX epoch time,
    or beat time."""

    name = "time"
    commands = ["time", "beats", "swatch", "epoch", "date"]

    def process(self, data: Data) -> None:
        if data.command in ["beats", "swatch"]:
            self.do_beats(data)
            return
        if data.command == "epoch":
            self.reply(data, time.time())
            return
        if data.args:
            timezone = data.args[0]
        else:
            timezone = "UTC"
        if timezone in ["beats", "swatch"]:
            self.do_beats(data)
        else:
            self.do_time(data, timezone)

    def do_beats(self, data: Data) -> None:
        beats = ((time.time() + 3600) % 86400) / 86.4
        beats = int(math.floor(beats))
        self.reply(data, f"@{beats:0>3}")

    def do_time(self, data: Data, tzname: str) -> None:
        try:
            tzinfo = ZoneInfo(tzname)
        except LookupError:
            self.reply(data, f"Unknown timezone: {timezone}")
            return
        now = datetime.now(tz=tzinfo)
        self.reply(data, now.strftime("%Y-%m-%d %H:%M:%S %Z"))
