# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2016 Ben Kurtovic <ben.kurtovic@gmail.com>
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

from collections import namedtuple
import re
import socket
from socket import AF_INET, AF_INET6

from earwigbot.commands import Command

_IP = namedtuple("_IP", ["family", "ip", "size"])
_Range = namedtuple("_Range", [
    "family", "range", "low", "high", "size", "addresses"])

class CIDR(Command):
    """Calculates the smallest CIDR range that encompasses a list of IP
    addresses. Used to make range blocks."""
    name = "cidr"
    commands = ["cidr", "range", "rangeblock", "rangecalc", "blockcalc",
                "iprange", "cdir"]

    # https://www.mediawiki.org/wiki/Manual:$wgBlockCIDRLimit
    LIMIT_IPv4 = 16
    LIMIT_IPv6 = 19

    def process(self, data):
        if not data.args:
            msg = ("Specify a list of IP addresses to calculate a CIDR range "
                   "for. For example, \x0306!{0} 192.168.0.3 192.168.0.15 "
                   "192.168.1.4\x0F or \x0306!{0} 2500:1:2:3:: "
                   "2500:1:2:3:dead:beef::\x0F.")
            self.reply(data, msg.format(data.command))
            return

        try:
            ips = [self._parse_ip(arg) for arg in data.args]
        except ValueError as exc:
            msg = "Can't parse IP address \x0302{0}\x0F."
            self.reply(data, msg.format(exc.message))
            return

        if any(ip.family == AF_INET for ip in ips) and any(
                ip.family == AF_INET6 for ip in ips):
            msg = "Can't calculate a range for both IPv4 and IPv6 addresses."
            self.reply(data, msg)
            return

        cidr = self._calculate_range(ips[0].family, ips)
        descr = self._describe(cidr.family, cidr.size)

        msg = ("Smallest CIDR range is \x02{0}\x0F, covering {1} from "
               "\x0305{2}\x0F to \x0305{3}\x0F{4}.")
        self.reply(data, msg.format(
            cidr.range, cidr.addresses, cidr.low, cidr.high,
            " (\x0304{0}\x0F)".format(descr) if descr else ""))

    def _parse_ip(self, arg):
        """Converts an argument into an IP address object."""
        arg = self._parse_arg(arg)
        oldarg = arg
        size = None
        if "/" in arg:
            arg, size = arg.split("/", 1)
            try:
                size = int(size, 10)
            except ValueError:
                raise ValueError(oldarg)
            if size < 0 or size > 128:
                raise ValueError(oldarg)

        try:
            ip = _IP(AF_INET, socket.inet_pton(AF_INET, arg), size)
        except socket.error:
            try:
                return _IP(AF_INET6, socket.inet_pton(AF_INET6, arg), size)
            except socket.error:
                raise ValueError(oldarg)
        if size > 32:
            raise ValueError(oldarg)
        return ip

    def _parse_arg(self, arg):
        """Converts an argument into an IP address string."""
        if "[[" in arg and "]]" in arg:
            regex = r"\[\[\s*(?:User(?:\stalk)?:)?(.*?)(?:\|.*?)?\s*\]\]"
            match = re.search(regex, arg, re.I)
            if not match:
                raise ValueError(arg)
            arg = match.group(1)

        if re.match(r"https?://", arg):
            if "target=" in arg:
                regex = r"target=(.*?)(?:&|$)"
            elif "page=" in arg:
                regex = r"page=(?:User(?:(?:\s|_)talk)?(?::|%3A))?(.*?)(?:&|$)"
            elif re.search(r"Special(:|%3A)Contributions/", arg, re.I):
                regex = r"Special(?:\:|%3A)Contributions/(.*?)(?:\&|\?|$)"
            elif re.search(r"User((\s|_)talk)?(:|%3A)", arg, re.I):
                regex = r"User(?:(?:\s|_)talk)?(?:\:|%3A)(.*?)(?:\&|\?|$)"
            else:
                raise ValueError(arg)
            match = re.search(regex, arg, re.I)
            if not match:
                raise ValueError(arg)
            arg = match.group(1)
        return arg

    def _calculate_range(self, family, ips):
        """Calculate the smallest CIDR range encompassing a list of IPs."""
        bin_ips = ["".join(
            bin(ord(octet))[2:].zfill(8) for octet in ip.ip) for ip in ips]
        for i, ip in enumerate(ips):
            if ip.size is not None:
                suffix = "X" * (len(bin_ips[i]) - ip.size)
                bin_ips[i] = bin_ips[i][:ip.size] + suffix

        size = len(bin_ips[0])
        for i in xrange(len(bin_ips[0])):
            if any(ip[i] == "X" for ip in bin_ips) or (
                    any(ip[i] == "0" for ip in bin_ips) and
                    any(ip[i] == "1" for ip in bin_ips)):
                size = i
                break

        bin_low = bin_ips[0][:size].ljust(len(bin_ips[0]), "0")
        bin_high = bin_ips[0][:size].ljust(len(bin_ips[0]), "1")
        low = self._format_bin(family, bin_low)
        high = self._format_bin(family, bin_high)

        return _Range(
            family, low + "/" + str(size), low, high, size,
            self._format_count(2 ** (len(bin_ips[0]) - size)))

    @staticmethod
    def _format_bin(family, binary):
        """Convert an IP's binary representation to presentation format."""
        return socket.inet_ntop(family, "".join(
            chr(int(binary[i:i + 8], 2)) for i in xrange(0, len(binary), 8)))

    @staticmethod
    def _format_count(count):
        """Nicely format a number of addresses affected by a range block."""
        if count == 1:
            return "1 address"
        if count > 2 ** 32:
            base = "{0:.2E} addresses".format(count)
            if count == 2 ** 64:
                return base + " (1 /64 subnet)"
            if count > 2 ** 96:
                return base + " ({0:.2E} /64 subnets)".format(count >> 64)
            if count > 2 ** 63:
                return base + " ({0:,} /64 subnets)".format(count >> 64)
            return base
        return "{0:,} addresses".format(count)

    def _describe(self, family, size):
        """Return an optional English description of a range."""
        if (family == AF_INET and size < self.LIMIT_IPv4) or (
                family == AF_INET6 and size < self.LIMIT_IPv6):
            return "too large to block"
