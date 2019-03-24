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

from earwigbot import exceptions
from earwigbot.commands import Command

class Lag(Command):
    """Return replag or maxlag information on specific databases."""
    name = "lag"
    commands = ["lag", "replag", "maxlag"]

    def process(self, data):
        site = self.get_site(data)
        if not site:
            return
        if data.command == "replag":
            base = "\x0302{0}\x0F: {1}."
            msg = base.format(site.name, self.get_replag(site))
        elif data.command == "maxlag":
            base = "\x0302{0}\x0F: {1}."
            msg = base.format(site.name, self.get_maxlag(site))
        else:
            base = "\x0302{0}\x0F: {1}; {2}."
            msg = base.format(site.name, self.get_replag(site),
                              self.get_maxlag(site))
        self.reply(data, msg)

    def get_replag(self, site):
        return "SQL replag is {0}".format(self.time(site.get_replag()))

    def get_maxlag(self, site):
        return "API maxlag is {0}".format(self.time(site.get_maxlag()))

    def get_site(self, data):
        if data.kwargs and "project" in data.kwargs and "lang" in data.kwargs:
            project, lang = data.kwargs["project"], data.kwargs["lang"]
            return self.get_site_from_proj_and_lang(data, project, lang)

        if not data.args:
            return self.bot.wiki.get_site()

        if len(data.args) > 1:
            name = " ".join(data.args)
            self.reply(data, "Unknown site: \x0302{0}\x0F.".format(name))
            return
        name = data.args[0]
        if "." in name:
            lang, project = name.split(".")[:2]
        elif ":" in name:
            project, lang = name.split(":")[:2]
        else:
            try:
                return self.bot.wiki.get_site(name)
            except exceptions.SiteNotFoundError:
                msg = "Unknown site: \x0302{0}\x0F.".format(name)
                self.reply(data, msg)
                return
        return self.get_site_from_proj_and_lang(data, project, lang)

    def get_site_from_proj_and_lang(self, data, project, lang):
        try:
            site = self.bot.wiki.get_site(project=project, lang=lang)
        except exceptions.SiteNotFoundError:
            try:
                site = self.bot.wiki.add_site(project=project, lang=lang)
            except exceptions.APIError:
                msg = "Site \x0302{0}:{1}\x0F not found."
                self.reply(data, msg.format(project, lang))
                return
        return site

    def time(self, seconds):
        parts = [("year", 31536000), ("day", 86400), ("hour", 3600),
                 ("minute", 60), ("second", 1)]
        msg = []
        for name, size in parts:
            num = seconds / size
            seconds -= num * size
            if num:
                chunk = "{0} {1}".format(num, name if num == 1 else name + "s")
                msg.append(chunk)
        return ", ".join(msg) if msg else "0 seconds"
