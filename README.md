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
made over 50,000 edits.

A project to rewrite it from scratch began in early April 2011, thus moving
away from the Pywikipedia framework and allowing for less overall code, better
integration between bot parts, and easier maintenance.

# Installation

This package contains the core `earwigbot`, abstracted enough that it should be
usable and customizable by anyone running a bot on a MediaWiki site. Since it's
component-based, the IRC components can be disabled if desired. IRC commands
and bot tasks specific to
[my instance of EarwigBot](http://en.wikipedia.org/wiki/User:EarwigBot) are
available from the package
[earwigbot-plugins](https://github.com/earwig/earwigbot-plugins).

## Latest release (v0.1)

EarwigBot is available from the [Python Package Index](http://pypi.python.org),
so you can install the latest release with `pip install earwigbot`
([get pip](http://pypi.python.org/pypi/pip)).

You can also install it from source directly:

    curl -Lo earwigbot.tgz "https://github.com/earwig/earwigbot/tarball/v0.1"
    tar -xf earwigbot.tgz
    cd earwig-earwigbot-*
    python setup.py install  # may require root, or use --user switch to install locally
    cd ..
    rm -r earwigbot.tgz earwig-earwigbot-*

## Development version

You can install the development version of the bot from `git`, probably on the
`develop` branch which contains (usually) working code. `master` contains the
latest release. EarwigBot uses
[git flow](http://nvie.com/posts/a-successful-git-branching-model/), so you're
free to browse by tags or by new features (`feature/*` branches).

    git clone git://github.com/earwig/earwigbot.git earwigbot
    cd earwigbot
    python setup.py develop  # may require root, or use --user switch to install locally

# Setup

It's recommended to run the bot's unit tests before installing. Run
`python -m unittest discover tests` from the project's root directory.

*Note:* some unit tests require an internet connection.

# Customizing

# Hacking
