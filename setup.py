#! /usr/bin/env python
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

from setuptools import setup, find_packages

from earwigbot import __version__

# Not all of these dependencies are required, particularly the copyvio-specific
# ones (bs4, lxml, nltk, and oauth2) and the command-specific one (pytz). The
# bot should run fine without them, but will raise an exception if you try to
# detect copyvios or run a command that requries one.

dependencies = [
    "PyYAML >= 3.10",  # Parsing config files
    "beautifulsoup4 >= 4.1.1",  # Parsing/scraping HTML for copyvios
    "lxml >= 2.3.5",  # Faster parser for BeautifulSoup
    "mwparserfromhell >= 0.1",  # Parsing wikicode for manipulation
    "nltk >= 2.0.2",  # Parsing sentences to split article content for copyvios
    "oauth2 >= 1.5.211",  # Interfacing with Yahoo! BOSS Search for copyvios
    "oursql >= 0.9.3.1",  # Interfacing with MediaWiki databases
    "py-bcrypt >= 0.2",  # Hashing the bot key in the config file
    "pycrypto >= 2.6",  # Storing bot passwords and keys in the config file
    "pytz >= 2012d",  # Handling timezones for the !time IRC command
]

with open("README.rst") as fp:
    long_docs = fp.read()

setup(
    name = "earwigbot",
    packages = find_packages(exclude=("tests",)),
    entry_points = {"console_scripts": ["earwigbot = earwigbot.util:main"]},
    install_requires = dependencies,
    test_suite = "tests",
    version = __version__,
    author = "Ben Kurtovic",
    author_email = "ben.kurtovic@verizon.net",
    url = "https://github.com/earwig/earwigbot",
    description = "EarwigBot is a Python robot that edits Wikipedia and interacts with people over IRC.",
    long_description = long_docs,
    download_url = "https://github.com/earwig/earwigbot/tarball/v{0}".format(__version__),
    keywords = "earwig earwigbot irc wikipedia wiki mediawiki",
    license = "MIT License",
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Communications :: Chat :: Internet Relay Chat",
        "Topic :: Internet :: WWW/HTTP"
    ],
)
