# -*- coding: utf-8  -*-

# EarwigBot Configuration File
# This file tells the bot which of its components should be enabled.

# The IRC frontend (configured in config/irc.py) sits on a public IRC network,
# responds to commands given to it, and reports edits (if the IRC watcher
# component is enabled).
enable_irc_frontend = True

# The IRC watcher (connection details configured in config/irc.py as well) sits
# on an IRC network that gives a recent changes feed, usually irc.wikimedia.net.
# It looks for edits matching certain (often regex) patterns (rules configured
# in config/watcher.py), and either reports them to the IRC frontend (if
# enabled), or activates a task on the WikiBot (if configured to do).
enable_irc_watcher = True

# EarwigBot doesn't have to edit a wiki, although this is its main purpose. If
# the wiki schedule is disabled, it will not be able to handle scheduled tasks
# that involve editing (such as creating a daily category every day at midnight
# UTC), but it can still edit through rules given in the watcher, and bot tasks
# can still be activated by the command line. The schedule is configured in
# config/schedule.py.
enable_wiki_schedule = True
