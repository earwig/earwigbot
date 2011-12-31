# -*- coding: utf-8  -*-
#
# Copyright (C) 2009, 2010, 2011 by Ben Kurtovic <ben.kurtovic@verizon.net>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
EarwigBot's IRC Watcher Rules

This file contains (configurable!) rules that EarwigBot's watcher uses after it
recieves an event from IRC.
"""

import re

from earwigbot import tasks

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
        chans.update(("##earwigbot", "#wikipedia-en-afc-feed"))

    if r_page.search(page_name):
        #tasks.start("afc_copyvios", page=rc.page)
        chans.add("#wikipedia-en-afc-feed")

    elif r_ffu.match(page_name):
        chans.add("#wikipedia-en-afc-feed")

    elif page_name.startswith("template:afc submission"):
        chans.add("#wikipedia-en-afc-feed")

    elif rc.flags == "move" and (r_move1.match(comment) or
                                 r_move2.match(comment)):
        p = r_moved_pages.findall(rc.comment)[0]
        chans.add("#wikipedia-en-afc-feed")

    elif rc.flags == "delete" and r_delete.match(comment):
        p = r_deleted_page.findall(rc.comment)[0]
        chans.add("#wikipedia-en-afc-feed")

    elif rc.flags == "restore" and r_restore.match(comment):
        p = r_restored_page.findall(rc.comment)[0]
        #tasks.start("afc_copyvios", page=p)
        chans.add("#wikipedia-en-afc-feed")

    elif rc.flags == "protect" and r_protect.match(comment):
        chans.add("#wikipedia-en-afc-feed")

    return chans
