# -*- coding: utf-8  -*-

# EarwigBot Configuration File
# This file contains information that the bot uses to connect to IRC.

# our main (front-end) server's hostname and port
HOST = "irc.freenode.net"
PORT = 6667

# our watcher server's hostname, port, and RC channel
WATCHER_HOST = "irc.wikimedia.org"
WATCHER_PORT = 6667
WATCHER_CHAN = "#en.wikipedia"

# our nick, ident, and real name, used on both servers
NICK = "EarwigBot"
IDENT = "earwigbot"
REALNAME = "[[w:en:User:EarwigBot]]"

# channels to join on main server's startup
CHANS = ["##earwigbot", "##earwig", "#wikipedia-en-afc"]
AFC_CHANS = ["#wikipedia-en-afc"] # report recent AfC changes/give AfC status messages upon join
BOT_CHANS = ["##earwigbot", "#wikipedia-en-afc"] # report edits containing "!earwigbot"

# hardcoded hostnames of users with certain permissions
OWNERS = ["wikipedia/The-Earwig"] # can use owner-only commands (!restart and !git)
ADMINS = ["wikipedia/The-Earwig", "wikipedia/LeonardBloom"] # can use high-risk commands, e.g. !op
