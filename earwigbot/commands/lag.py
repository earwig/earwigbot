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

from earwigbot import exceptions
from earwigbot.commands import Command

class Lag(Command):
    """Return the replag for a specific database on the Toolserver."""
    name = "lag"
    commands = ["lag", "replag", "maxlag"]

    def process(self, data):
        site = self.get_site(data)
        if not site:
            return

        msg = "\x0302{0}\x0F: Toolserver replag is {1} seconds; database maxlag is {2} seconds."
        msg = msg.format(site.name, site.get_replag(), site.get_maxlag())
        self.reply(data, msg)

    def get_site(self, data):
        if data.kwargs and "project" in data.kwargs and "lang" in data.kwargs:
            project, lang = data.kwargs["project"], data.kwargs["lang"]
            return self.get_site_from_proj_and_lang(data, project, lang)

        if not data.args:
            return self.bot.wiki.get_site()

        if len(data.args) > 1:
            name = " ".join(data.args)
            self.reply(data, "unknown site: \x0302{0}\x0F.".format(name))
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
                msg = "unknown site: \x0302{0}\x0F.".format(name)
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
                msg = "site \x0302{0}:{1}\x0F not found."
                self.reply(data, msg.format(project, lang))
                return
        return site
