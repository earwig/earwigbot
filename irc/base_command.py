# -*- coding: utf-8  -*-

# A base class for commands on IRC.

class BaseCommand(object):
    def __init__(self, connection):
        """docstring"""
        self.connection = connection

    def get_hook(self):
        """Hooks are: 'msg', 'msg_private', 'msg_public', and 'join'."""
        return None

    def get_help(self, command):
        """docstring"""
        return None

    def check(self, data):
        """docstring"""
        return False

    def process(self, data):
        """docstring"""
        pass
