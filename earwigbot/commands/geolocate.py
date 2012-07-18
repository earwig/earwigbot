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

import json
import urllib2

from earwigbot.commands import Command

class Geolocate(Command):
    """Geolocate an IP address (via http://ipinfodb.com/)."""
    name = "geolocate"
    commands = ["geolocate", "locate", "geo", "ip"]

    def setup(self):
        self.config.decrypt(self.config.commands, self.name, "apiKey")
        try:
            self.key = self.config.commands[self.name]["apiKey"]
        except KeyError:
            self.key = None
            log = 'Cannot use without an API key for http://ipinfodb.com/ stored as config.commands["{0}"]["apiKey"]'
            self.logger.warn(log.format(self.name))

    def process(self, data):
        if not data.args:
            self.reply(data, "Please specify an IP to lookup.")
            return

        if not self.key:
            msg = 'I need an API key for http://ipinfodb.com/ stored as \x0303config.commands["{0}"]["apiKey"]\x0F.'
            log = 'Need an API key for http://ipinfodb.com/ stored as config.commands["{0}"]["apiKey"]'
            self.reply(data, msg.format(self.name) + ".")
            self.logger.error(log.format(self.name))
            return

        address = data.args[0]
        url = "http://api.ipinfodb.com/v3/ip-city/?key={0}&ip={1}&format=json"
        query = urllib2.urlopen(url.format(self.key, address)).read()
        res = json.loads(query)

        country = res["countryName"].title()
        region = res["regionName"].title()
        city = res["cityName"].title()
        latitude = res["latitude"]
        longitude = res["longitude"]
        utcoffset = res["timeZone"]
        if not country and not region and not city:
            self.reply(data, "IP \x0302{0}\x0F not found.".format(address))
            return
        if country == "-" and region == "-" and city == "-":
            self.reply(data, "IP \x0302{0}\x0F is reserved.".format(address))
            return

        msg = "{0}, {1}, {2} ({3}, {4}), UTC {5}"
        geo = msg.format(country, region, city, latitude, longitude, utcoffset)
        self.reply(data, geo)
