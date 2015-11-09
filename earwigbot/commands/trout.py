# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from unicodedata import normalize

from earwigbot.commands import Command

class Trout(Command):
    """Slap someone with a trout, or related fish."""
    name = "trout"
    commands = ["trout", "whale"]

    def setup(self):
        try:
            self.exceptions = self.config.commands[self.name]["exceptions"]
        except KeyError:
            self.exceptions = {}

    def process(self, data):
        animal = data.command
        target = " ".join(data.args) or data.nick
        target = "himself" if target == "yourself" else target

        normal = normalize("NFKD", target.decode("utf8")).lower()
        if normal in self.exceptions:
            self.reply(data, self.exceptions[normal])
        else:
            msg = "slaps \x02{0}\x0F around a bit with a large {1}."
            self.action(data.chan, msg.format(target, animal))
