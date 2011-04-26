# -*- coding: utf-8  -*-

# EarwigBot Configuration File
# This file contains rules for the bot's watcher component.

import re

AFC_CHANS = ["#wikipedia-en-afc"] # report recent AfC changes/give AfC status messages upon join
BOT_CHANS = ["##earwigbot", "#wikipedia-en-afc"] # report edits containing "!earwigbot"

def process(rc):
    chans = set() # channels to report this message to
    page_name = rc.page.lower()
    
    if "!earwigbot" in rc.msg.lower():
        chans.update(BOT_CHANS)
        
    if re.match("wikipedia( talk)?:(wikiproject )?articles for creation", page_name):
        chans.update(AFC_CHANS)
        
    elif re.match("wikipedia( talk)?:files for upload", page_name):
        chans.update(AFC_CHANS)
        
    elif page_name.startswith("template:afc submission"):
        chans.update(AFC_CHANS)
        
    elif rc.flags == "delete" and re.match("deleted \"\[\[wikipedia( talk)?:(wikiproject )?articles for creation", rc.comment.lower()):
        chans.update(AFC_CHANS)
        
    elif rc.flags == "protect" and re.match("protected \"\[\[wikipedia( talk)?:(wikiproject )?articles for creation", rc.comment.lower()):
        chans.update(AFC_CHANS)

    return chans
