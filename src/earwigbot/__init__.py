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

"""
`EarwigBot <https://github.com/earwig/earwigbot>`_ is a Python robot that edits
Wikipedia and interacts over IRC.

See :file:`README.rst` for an overview, or the :file:`docs/` directory for details.
This documentation is also available `online <https://packages.python.org/earwigbot>`_.
"""

__all__ = [
    "bot",
    "cli",
    "commands",
    "config",
    "exceptions",
    "irc",
    "managers",
    "tasks",
    "wiki",
]
__author__ = "Ben Kurtovic"
__copyright__ = "Copyright (C) 2009-2024 Ben Kurtovic"
__license__ = "MIT License"
__version__ = "0.4"
__email__ = "ben.kurtovic@gmail.com"
__release__ = False

if not __release__:

    def _get_git_commit_id():
        """Return the ID of the git HEAD commit."""
        from os.path import dirname, split

        from git import Repo

        path = split(dirname(__file__))[0]
        commit_id = Repo(path).head.object.hexsha
        return commit_id[:8]

    try:
        __version__ += "+" + _get_git_commit_id()
    except Exception:
        pass
    finally:
        del _get_git_commit_id

from earwigbot import (
    bot,
    cli,
    commands,
    config,
    exceptions,
    irc,
    managers,
    tasks,
    wiki,
)
