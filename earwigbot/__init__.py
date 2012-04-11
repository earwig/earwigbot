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

"""
EarwigBot is a Python robot that edits Wikipedia and interacts with people over
IRC. - https://github.com/earwig/earwigbot

See README.rst for an overview, or the docs/ directory for details. This
documentation is also available online at http://packages.python.org/earwigbot.
"""

__author__ = "Ben Kurtovic"
__copyright__ = "Copyright (C) 2009, 2010, 2011, 2012 by Ben Kurtovic"
__license__ = "MIT License"
__version__ = "0.1.dev"
__email__ = "ben.kurtovic@verizon.net"
__release__ = False

if not __release__:
    def _add_git_commit_id_to_version_string(version):
        from git import Repo
        from os.path import split, dirname
        path = split(dirname(__file__))[0]
        commit_id = Repo(path).head.object.hexsha
        return version + ".git+" + commit_id[:8]
    try:
        __version__ = _add_git_commit_id_to_version_string(__version__)
    except Exception:
        pass
    finally:
        del _add_git_commit_id_to_version_string

from earwigbot import blowfish, bot, config, managers, util  # Modules
from earwigbot import commands, irc, tasks, wiki  # Subpackages
