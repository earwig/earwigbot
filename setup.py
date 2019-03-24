#! /usr/bin/env python
# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2019 Ben Kurtovic <ben.kurtovic@gmail.com>
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

required_deps = [
    "PyYAML >= 3.12",  # Parsing config files
    "mwparserfromhell >= 0.5",  # Parsing wikicode for manipulation
    "requests >= 2.21.0",  # Wiki API requests
    "requests_oauthlib >= 1.2.0",  # API authentication via OAuth
]

extra_deps = {
    "crypto": [
        "py-bcrypt >= 0.4",  # Hashing the bot key in the config file
        "pycrypto >= 2.6.1",  # Storing bot passwords + keys in the config file
    ],
    "sql": [
        "oursql >= 0.9.3.2",  # Interfacing with MediaWiki databases
    ],
    "copyvios": [
        "beautifulsoup4 >= 4.6.0",  # Parsing/scraping HTML
        "cchardet >= 2.1.1",  # Encoding detection for BeautifulSoup
        "lxml >= 3.8.0",  # Faster parser for BeautifulSoup
        "nltk >= 3.2.4",  # Parsing sentences to split article content
        "oauth2 >= 1.9.0",  # Interfacing with Yahoo! BOSS Search
        "pdfminer >= 20140328",  # Extracting text from PDF files
        "tldextract >= 2.1.0",  # Getting domains for the multithreaded workers
    ],
    "time": [
        "pytz >= 2017.2",  # Handling timezones for the !time IRC command
    ],
}

dependencies = required_deps + sum(extra_deps.values(), [])

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
    author_email = "ben.kurtovic@gmail.com",
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
