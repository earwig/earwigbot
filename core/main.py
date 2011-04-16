# -*- coding: utf-8  -*-

## EarwigBot's Core
## Basically, this creates threads for our IRC watcher component and Wikipedia component, and then runs the main IRC bot on the main thread.

## The IRC bot component of EarwigBot has two parts: a front-end and a watcher.
## The front-end runs on a normal IRC server and expects users to interact with it/give it commands.
## The watcher runs on a wiki recent-changes server and listens for edits. Users cannot interact with this part of the bot.

import threading
import time
import traceback
import sys
import os

parent_dir = os.path.split(sys.path[0])[0]
sys.path.append(parent_dir) # make sure we look in the parent directory for modules

from irc import frontend, watcher

f_conn = None
w_conn = None

def irc_watcher(f_conn):
    global w_conn
    while 1: # restart the watcher component if (just) it breaks
        w_conn = watcher.get_connection()
        try:
            watcher.main(w_conn, f_conn)
        except:
            traceback.print_exc()
        time.sleep(5) # sleep a bit before restarting watcher
        print "watcher has stopped; restarting component..."

def run():
    global f_conn
    f_conn = frontend.get_connection()
    
    t_watcher = threading.Thread(target=irc_watcher, args=(f_conn,))
    t_watcher.daemon = True
    t_watcher.start()

    frontend.main(f_conn)

    w_conn.close()
    f_conn.close()

if __name__ == "__main__":
    run()
