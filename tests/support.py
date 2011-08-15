# -*- coding: utf-8  -*-

"""
EarwigBot's Unit Test Support

This module provides some support code for unit tests.

Importing this module will "fix" your path so that EarwigBot code from bot/
can be imported normally. The run() function runs a given test case.
"""

from os import path
import sys
import unittest

root = path.join(path.split(path.dirname(path.abspath(__file__)))[0], "bot")
sys.path.insert(0, root)

def run(case):
    suite = unittest.TestLoader().loadTestsFromTestCase(case)
    text_runner = unittest.TextTestRunner(verbosity=2).run(suite)
