# -*- coding: utf-8  -*-

## EarwigBot's Core

## EarwigBot has three components that can run independently of each other: an
## IRC front-end, an IRC watcher, and a wiki scheduler.
## * The IRC front-end runs on a normal IRC server and expects users to
##   interact with it/give it commands.
## * The IRC watcher runs on a wiki recent-changes server and listens for
##   edits. Users cannot interact with this part of the bot.
## * The wiki scheduler runs wiki-editing bot tasks in separate threads at
##   user-defined times through a cron-like interface.

## There is a "priority" system here:
## 1. If the IRC frontend is enabled, it will run on the main thread, and the
##    IRC watcher and wiki scheduler (if enabled) will run on separate threads.
## 2. If the wiki scheduler is enabled, it will run on the main thread, and the
##    IRC watcher (if enabled) will run on a separate thread.
## 3. If the IRC watcher is enabled, it will run on the main (and only) thread.
## Else, the bot will stop, as no components are enabled.

import threading
import time
import traceback
import sys
import os

parent_dir = os.path.split(sys.path[0])[0]
sys.path.append(parent_dir) # make sure we look in the parent directory for modules

from config.main import *
from irc import frontend, watcher
from wiki import task_manager

f_conn = None
w_conn = None

def irc_watcher(f_conn):
    """Function to handle the IRC watcher as another thread (if frontend and/or
    scheduler is enabled), otherwise run as the main thread."""
    global w_conn
    print "\nStarting IRC watcher..."
    while 1: # restart the watcher component if (just) it breaks
        w_conn = watcher.get_connection()
        w_conn.connect()
        print # print a blank line here to signify that the bot has finished starting up
        try:
            watcher.main(w_conn, f_conn)
        except:
            traceback.print_exc()
        time.sleep(5) # sleep a bit before restarting watcher
        print "\nWatcher has stopped; restarting component..."

def wiki_scheduler():
    """Function to handle the wiki scheduler as another thread, or as the
    primary thread if the IRC frontend is not enabled."""
    while 1:
        time_start = time.time()
        now = time.gmtime(time_start)
        
        task_manager.start_tasks(now)
        
        time_end = time.time()
        time_diff = time_start - time_end
        if time_diff < 60: # sleep until the next minute
            time.sleep(60 - time_diff)

def irc_frontend():
    """If the IRC frontend is enabled, make it run on our primary thread, and
    enable the wiki scheduler and IRC watcher on new threads if they are
    enabled."""
    global f_conn
    
    print "\nStarting IRC frontend..."
    f_conn = frontend.get_connection()
    frontend.startup(f_conn)
    
    if enable_wiki_schedule:
        print "\nStarting wiki scheduler..."
        task_manager.load_tasks()
        t_scheduler = threading.Thread(target=wiki_scheduler)
        t_scheduler.name = "wiki-scheduler"
        t_scheduler.daemon = True
        t_scheduler.start()
    
    if enable_irc_watcher:
        t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
        t_watcher.name = "irc-watcher"
        t_watcher.daemon = True
        t_watcher.start()

    frontend.main()

    if enable_irc_watcher:
        w_conn.close()
    f_conn.close()
    
def run():
    if enable_irc_frontend: # make the frontend run on our primary thread if enabled, and enable additional components through that function
        irc_frontend()
    
    elif enable_wiki_schedule: # the scheduler is enabled - run it on the main thread, but also run the IRC watcher on another thread if it is enabled
        print "\nStarting wiki scheduler..."
        task_manager.load_tasks()
        if enable_irc_watcher:
            t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
            t_watcher.name = "irc-watcher"
            t_watcher.daemon = True
            t_watcher.start()
        wiki_scheduler()
    
    elif enable_irc_watcher: # the IRC watcher is our only enabled component, so run its function only and don't worry about anything else
        irc_watcher()
        
    else: # nothing is enabled!
        exit("\nNo bot parts are enabled; stopping...")

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        exit("\nKeyboardInterrupt: stopping main bot loop.")
