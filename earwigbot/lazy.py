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

"""
Implements a hierarchy of importing classes as defined in PEP 302 to load
modules in a safe yet lazy manner.
"""

from imp import acquire_lock, release_lock
import sys
from types import ModuleType

__all__ = ["LazyImporter"]

def _getattribute(self, attr):
    _load(self)
    return self.__getattribute__(attr)

def _setattr(self, attr, value):
    _load(self)
    self.__setattr__(attr, value)

def _load(self):
    type(self).__getattribute__ = ModuleType.__getattribute__
    type(self).__setattr__ = ModuleType.__setattr__
    reload(self)


class _LazyModule(type):
    def __new__(cls, name):
        acquire_lock()
        try:
            if name not in sys.modules:
                attributes = {
                    "__name__": name,
                    "__getattribute__": _getattribute,
                    "__setattr__": _setattr
                }
                parents = (ModuleType,)
                klass = type.__new__(cls, "module", parents, attributes)
                sys.modules[name] = klass(name)
            return sys.modules[name]
        finally:
            release_lock()


class LazyImporter(object):
    def __init__(self):
        self._modules = {}
        sys.meta_path.append(self)

    def new(self, name):
        module = _LazyModule(name)
        self._modules[name] = module
        return module

    def find_module(self, fullname, path=None):
        if fullname in self._modules and fullname not in sys.modules:
            return self

    def load_module(self, fullname):
        return self._modules.pop(fullname)
