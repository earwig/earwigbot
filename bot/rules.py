# -*- coding: utf-8  -*-

"""
EarwigBot's IRC Watcher Rules

This file contains (configurable!) rules that EarwigBot's watcher uses after it
recieves an event from IRC.
"""

import re

import tasks

afc_prefix = "wikipedia( talk)?:(wikiproject )?articles for creation"

# compile some regexps used when finding specific events
r_page = re.compile(afc_prefix)
r_ffu = re.compile("wikipedia( talk)?:files for upload")
r_move1 = re.compile("moved \[\[{}".format(afc_prefix))
r_move2 = re.compile("moved \[\[(.*?)\]\] to \[\[{}".format(afc_prefix))
r_moved_pages = re.compile("^moved \[\[(.*?)\]\] to \[\[(.*?)\]\]")
r_delete = re.compile("deleted \"\[\[{}".format(afc_prefix))
r_deleted_page = re.compile("^deleted \"\[\[(.*?)\]\]")
r_restore = re.compile("restored \"\[\[{}".format(afc_prefix))
r_restored_page = re.compile("^restored \"\[\[(.*?)\]\]")
r_protect = re.compile("protected \"\[\[{}".format(afc_prefix))

def process(rc):
    """Given an RC() object, return a list of channels to report this event to.
    Also, start any wiki bot tasks within this function if necessary."""
    chans = set()  # channels to report this message to
    page_name = rc.page.lower()
    comment = rc.comment.lower()
    
    if "!earwigbot" in rc.msg.lower():
        chans.update(("##earwigbot", "#wikipedia-en-afc"))
        
    if r_page.search(page_name):
        tasks.start("afc_statistics", action="edit", page=rc.page)
        tasks.start("afc_copyvios", action="edit", page=rc.page)
        chans.add("#wikipedia-en-afc")
        
    elif r_ffu.match(page_name):
        chans.add("#wikipedia-en-afc")
        
    elif page_name.startswith("template:afc submission"):
        chans.add("#wikipedia-en-afc")
    
    elif rc.flags == "move" and (r_move1.match(comment) or
                                 r_move2.match(comment)):
        p = r_moved_pages.findall(rc.comment)[0]
        tasks.start("afc_statistics", action="move", page=p)
        tasks.start("afc_copyvios", action="move", page=p)
        chans.add("#wikipedia-en-afc")
    
    elif rc.flags == "delete" and r_delete.match(comment):
        p = r_deleted_page.findall(rc.comment)[0]
        tasks.start("afc_statistics", action="delete", page=p)
        tasks.start("afc_copyvios", action="delete", page=p)
        chans.add("#wikipedia-en-afc")
    
    elif rc.flags == "restore" and r_restore.match(comment):
        p = r_restored_page.findall(rc.comment)[0]
        tasks.start("afc_statistics", action="restore", page=p)
        tasks.start("afc_copyvios", action="restore", page=p)
        chans.add("#wikipedia-en-afc")
    
    elif rc.flags == "protect" and r_protect.match(comment):
        chans.add("#wikipedia-en-afc")

    return chans
