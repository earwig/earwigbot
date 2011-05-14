# -*- coding: utf-8  -*-

# EarwigBot Configuration File
# This file contains rules for the bot's watcher component.

import re

from wiki import task_manager

# Define different report channels on our front-end server. They /must/ be in CHANS in config/irc.py or the bot will not be able to send messages to them (unless they have -n set).
AFC_CHANS = ["#wikipedia-en-afc"] # report recent AfC changes/give AfC status messages upon join
BOT_CHANS = ["##earwigbot", "#wikipedia-en-afc"] # report edits containing "!earwigbot"

# Define some commonly used strings.
afc_prefix = "wikipedia( talk)?:(wikiproject )?articles for creation"

# Define our compiled regexps used when finding certain edits.
r_page = re.compile(afc_prefix)
r_ffu = re.compile("wikipedia( talk)?:files for upload")
r_move1 = re.compile("moved \[\[{}".format(afc_prefix)) # an AFC page was either moved locally or out
r_move2 = re.compile("moved \[\[(.*?)\]\] to \[\[{}".format(afc_prefix)) # an outside page was moved into AFC
r_moved_pages = re.compile("^moved \[\[(.*?)\]\] to \[\[(.*?)\]\]")
r_delete = re.compile("deleted \"\[\[{}".format(afc_prefix))
r_deleted_page = re.compile("^deleted \"\[\[(.*?)\]\]")
r_restore = re.compile("restored \"\[\[{}".format(afc_prefix))
r_restored_page = re.compile("^restored \"\[\[(.*?)\]\]")
r_protect = re.compile("protected \"\[\[{}".format(afc_prefix))

def process(rc):
    chans = set() # channels to report this message to
    page_name = rc.page.lower()
    comment = rc.comment.lower()
    
    if "!earwigbot" in rc.msg.lower():
        chans.update(BOT_CHANS)
        
    if r_page.search(page_name):
        task_manager.start_task("afc_statistics", action="process_edit", page=rc.page)
        task_manager.start_task("afc_copyvios", action="process_edit", page=rc.page)
        chans.update(AFC_CHANS)
        
    elif r_ffu.match(page_name):
        chans.update(AFC_CHANS)
        
    elif page_name.startswith("template:afc submission"):
        chans.update(AFC_CHANS)
    
    elif rc.flags == "move" and (r_move1.match(comment) or r_move2.match(comment)):
        p = r_moved_pages.findall(rc.comment)[0]
        task_manager.start_task("afc_statistics", action="process_move", pages=p)
        task_manager.start_task("afc_copyvios", action="process_move", pages=p)
        chans.update(AFC_CHANS)
    
    elif rc.flags == "delete" and r_delete.match(comment):
        p = r_deleted_page.findall(rc.comment)[0][0]
        task_manager.start_task("afc_statistics", action="process_delete", page=p)
        task_manager.start_task("afc_copyvios", action="process_delete", page=p)
        chans.update(AFC_CHANS)
    
    elif rc.flags == "restore" and r_restore.match(comment):
        p = r_restored_page.findall(rc.comment)[0][0]
        task_manager.start_task("afc_statistics", action="process_restore", page=p)
        task_manager.start_task("afc_copyvios", action="process_restore", page=p)
        chans.update(AFC_CHANS)
    
    elif rc.flags == "protect" and r_protect.match(comment):
        chans.update(AFC_CHANS)

    return chans
