[EarwigBot](http://en.wikipedia.org/wiki/User:EarwigBot) is a
[Python](http://python.org/) robot that edits
[Wikipedia](http://en.wikipedia.org/) and interacts with people over
[IRC](http://en.wikipedia.org/wiki/Internet_Relay_Chat).

# History

Development began, based on the
[Pywikipedia framework](http://pywikipediabot.sourceforge.net/), in early 2009.
Approval for its fist task, a
[copyright violation detector](http://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/EarwigBot_1),
was carried out in May, and the bot has been running consistently ever since
(with the exception of Jan/Feb 2011). It currently handles
[several ongoing tasks](http://en.wikipedia.org/wiki/User:EarwigBot#Tasks),
ranging from statistics generation to category cleanup, and on-demand tasks
such as WikiProject template tagging. Since it started running, the bot has
made over 45,000 edits.

A project to rewrite it from scratch began in early April 2011, thus moving
away from the Pywikipedia framework and allowing for less overall code, better
integration between bot parts, and easier maintenance.

# Installation

## Dependencies

EarwigBot uses the MySQL library
[oursql](http://packages.python.org/oursql/) (>= 0.9.2) for communicating with
MediaWiki databases, and some tasks use their own tables for storage.
Additionally, the afc_history task uses
[matplotlib](http://matplotlib.sourceforge.net/) and
[numpy](http://numpy.scipy.org/) for graphing AfC statistics. Neither of these
modules are required for the main bot itself.

`earwigbot.wiki.copyright` requires access to a search engine for detecting
copyright violations. Currently,
[Yahoo! BOSS](http://developer.yahoo.com/search/boss/) is the only engine
supported, and this requires
[oauth2](https://github.com/simplegeo/python-oauth2).
