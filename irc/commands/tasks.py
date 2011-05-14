# -*- coding: utf-8  -*-

# Manage wiki tasks from IRC, and check on thread status.

import threading

from irc.base_command import BaseCommand
from wiki import task_manager
from config.irc import *

class Tasks(BaseCommand):
    def get_hooks(self):
        return ["msg"]

    def get_help(self, command):
        return "Manage wiki tasks from IRC, and check on thread status."

    def check(self, data):
        if data.is_command and data.command in ["tasks", "threads", "tasklist"]:
            return True
        return False

    def process(self, data):
        self.data = data
        if data.host not in OWNERS:
            self.connection.reply(data, "at this time, you must be a bot owner to use this command.")
            return

        if not data.args:
            if data.command == "!tasklist":
                self.do_list()
            else:
                self.connection.reply(data, "no arguments provided. Maybe you wanted '!{cmnd} list', '!{cmnd} start', or '!{cmnd} listall'?".format(cmnd=data.command))
            return
        
        if data.args[0] == "list":
            self.do_list()
        
        elif data.args[0] == "start":
            self.do_start()
        
        elif data.args[0] == "listall":
            self.do_listall()

        else: # they asked us to do something we don't know
            self.connection.reply(data, "unknown argument: \x0303{}\x0301.".format(data.args[0]))

    def do_list(self):
        threads = threading.enumerate()
        for thread in threads:
            self.connection.reply(data, thread.name)
    
    def do_listall(self):
        tasks = task_manager.task_list.keys()
        self.connection.reply(data, ', '.join(tasks))
    
    def do_start(self):
        kwargs = {}
        try:
            task_manager.start_task(data.args[1], **kwargs)
        except IndexError: # no task name given
            self.connection.reply(data, "what task do you want me to start?")
        else:
            self.connection.reply(data, "task '{}' started.".format(data.args[1]))
