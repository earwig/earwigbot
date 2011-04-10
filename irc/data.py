# -*- coding: utf-8  -*-

# A class to store data from an individual line received on IRC.

class Data:
    def __init__(self):
        """store data from an individual line received on IRC"""
        self.chan = None
        self.nick = None
        self.ident = None
        self.host = None
        self.msg = None
