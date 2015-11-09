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

from collections import OrderedDict

__all__ = ["ConfigNode"]

class ConfigNode(object):
    def __init__(self):
        self._data = OrderedDict()

    def __repr__(self):
        return self._data

    def __nonzero__(self):
        return bool(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, item):
        self._data[key] = item

    def __getattr__(self, key):
        if key == "_data":
            return super(ConfigNode, self).__getattr__(key)
        return self._data[key]

    def __setattr__(self, key, item):
        if key == "_data":
            super(ConfigNode, self).__setattr__(key, item)
        else:
            self._data[key] = item

    def __iter__(self):
        for key in self._data:
            yield key

    def __contains__(self, item):
        return item in self._data

    def _dump(self):
        data = self._data.copy()
        for key, val in data.iteritems():
            if isinstance(val, ConfigNode):
                data[key] = val._dump()
        return data

    def _load(self, data):
        self._data = data.copy()

    def _decrypt(self, cipher, intermediates, item):
        base = self._data
        for inter in intermediates:
            try:
                base = base[inter]
            except KeyError:
                return
        if item in base:
            ciphertext = base[item].decode("hex")
            base[item] = cipher.decrypt(ciphertext).rstrip("\x00")

    def get(self, *args, **kwargs):
        return self._data.get(*args, **kwargs)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def iterkeys(self):
        return self._data.iterkeys()

    def itervalues(self):
        return self._data.itervalues()

    def iteritems(self):
        return self._data.iteritems()
