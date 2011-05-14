# -*- coding: utf-8  -*-

# Manage wiki tasks from IRC, and check on thread status.

import threading

from irc.base_command import BaseCommand
from wiki import task_manager
from config.main import *
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
            if data.command == "tasklist":
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
        
        normal_threads = []
        task_threads = []
        task_thread_num = 0
        
        for thread in threads:
            tname = thread.name
            if tname == "MainThread":
                tname = self.get_main_thread_name()
                normal_threads.append("\x0302{}\x0301 (as main thread, id {})".format(tname, thread.ident))
            elif tname in ["irc-frontend", "irc-watcher", "wiki-scheduler"]:
                normal_threads.append("\x0302{}\x0301 (id {})".format(tname, thread.ident))
            else:
                task_thread_num += 1
                task_threads.append("\x0302{}\x0301 (id {})".format(tname, thread.ident))
        
        if task_threads:
            msg = "\x02{}\x0F threads active: {}, and \x02{}\x0F task threads: {}.".format(len(threads), ', '.join(normal_threads), task_thread_num, ', '.join(task_threads))
        else:
            msg = "\x02{}\x0F threads active: {}, and \x020\x0F task threads.".format(len(threads), ', '.join(normal_threads))
        self.connection.reply(self.data, msg)
    
    def do_listall(self):
        tasks = task_manager.task_list.keys()
        self.connection.reply(self.data, ', '.join(tasks))
    
    def do_start(self):
        kwargs = {}
        try:
            task_manager.start_task(self.data.args[1], **kwargs)
        except IndexError: # no task name given
            self.connection.reply(self.data, "what task do you want me to start?")
        else:
            self.connection.reply(self.data, "task '{}' started.".format(self.data.args[1]))

    def get_main_thread_name(self):
        """Return the "proper" name of the MainThread; e.g. "irc-frontend" or "irc-watcher"."""
        if enable_irc_frontend:
            return "irc-frontend"
        elif enable_wiki_schedule:
            return "wiki-scheduler"
        else:
            return "irc-watcher"
