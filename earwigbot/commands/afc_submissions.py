# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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

from earwigbot.commands import Command

class AFCSubmissions(Command):
    """Link the user directly to some pending AFC submissions."""
    name = "submissions"
    commands = ["submissions", "subs"]

    def setup(self):
        try:
            self.ignore_list = self.config.commands[self.name]["ignoreList"]
        except KeyError:
            try:
                ignores = self.config.tasks["afc_statistics"]["ignoreList"]
                self.ignore_list = ignores
            except KeyError:
                self.ignore_list = []

    def process(self, data):
        if data.args:
            try:
                number = int(data.args[0])
            except ValueError:
                self.reply(data, "Argument must be a number.")
                return
            if number > 5:
                msg = "Cannot get more than five submissions at a time."
                self.reply(data, msg)
                return
        else:
            number = 3

        site = self.bot.wiki.get_site()
        category = site.get_category("Pending AfC submissions")
        members = category.get_members(limit=number + len(self.ignore_list))
        urls = [member.url.encode("utf8") for member in members if member.title not in self.ignore_list]
        pages = ", ".join(urls[:number])
        self.reply(data, "{0} pending AfC subs: {1}".format(number, pages))
