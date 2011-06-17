#! /usr/bin/python
# -*- coding: utf-8  -*-

"""
EarwigBot's Core

This (should) not be run directly; the wrapper in "earwigbot.py" is preferred,
but it should work fine alone, as long as you enter the password-unlock key at
the initial hidden prompt.

The core is essentially responsible for starting the various bot components
(irc, scheduler, etc) and making sure they are all happy. An explanation of the
different components follows:

EarwigBot has three components that can run independently of each other: an IRC
front-end, an IRC watcher, and a wiki scheduler.
* The IRC front-end runs on a normal IRC server and expects users to interact
  with it/give it commands.
* The IRC watcher runs on a wiki recent-changes server and listens for edits.
  Users cannot interact with this part of the bot.
* The wiki scheduler runs wiki-editing bot tasks in separate threads at
  user-defined times through a cron-like interface.

There is a "priority" system here:
1. If the IRC frontend is enabled, it will run on the main thread, and the IRC
   watcher and wiki scheduler (if enabled) will run on separate threads.
2. If the wiki scheduler is enabled, it will run on the main thread, and the
   IRC watcher (if enabled) will run on a separate thread.
3. If the IRC watcher is enabled, it will run on the main (and only) thread.
Else, the bot will stop, as no components are enabled.
"""

import threading
import time
import traceback
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.split(script_dir)[0]  # the bot's "root" directory relative
                                         # to its different components
sys.path.append(root_dir)  # make sure we look in the root dir for modules

from core import config
#from irc import frontend, watcher
#from wiki import task_manager

f_conn = None
w_conn = None

def irc_watcher(f_conn=None):
    """Function to handle the IRC watcher as another thread (if frontend and/or
    scheduler is enabled), otherwise run as the main thread."""
    global w_conn
    while 1:  # restart the watcher component if it breaks (and nothing else)
        w_conn = watcher.get_connection()
        w_conn.connect()
        print  # blank line to signify that the bot has finished starting up
        try:
            watcher.main(w_conn, f_conn)
        except:
            traceback.print_exc()
        time.sleep(5)  # sleep a bit before restarting watcher
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
        if time_diff < 60:  # sleep until the next minute
            time.sleep(60 - time_diff)

def irc_frontend(components):
    """If the IRC frontend is enabled, make it run on our primary thread, and
    enable the wiki scheduler and IRC watcher on new threads if they are
    enabled."""
    global f_conn

    print "Starting IRC frontend..."
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
        print "\nStarting IRC watcher..."
        t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
        t_watcher.name = "irc-watcher"
        t_watcher.daemon = True
        t_watcher.start()

    frontend.main()

    if enable_irc_watcher:
        w_conn.close()
    f_conn.close()

def run():
    try:
        key = raw_input()  # wait for our password unlock key from the bot's
    except EOFError:       # wrapper
        key = None
    config.parse_config(key)  # load data from the config file and parse it
                              # using the unlock key
    components = config.config.components

    if components["irc_frontend"]:  # make the frontend run on our primary
        irc_frontend(components)    # thread if enabled, and enable additional
                                    # components through that function

    elif components["wiki_schedule"]:       # run the scheduler on the main
        print "Starting wiki scheduler..."  # thread, but also run the IRC
        task_manager.load_tasks()           # watcher on another thread iff it
        if enable_irc_watcher:              # is enabled
            print "\nStarting IRC watcher..."
            t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
            t_watcher.name = "irc-watcher"
            t_watcher.daemon = True
            t_watcher.start()
        wiki_scheduler()

    elif components["irc_watcher"]:      # the IRC watcher is our only enabled
        print "Starting IRC watcher..."  # component, so run its function only
        irc_watcher()                    # and don't worry about anything else

    else:  # nothing is enabled!
        print "No bot parts are enabled; stopping..."
        exit(1)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print "\nKeyboardInterrupt: stopping main bot loop."
        exit(1)
