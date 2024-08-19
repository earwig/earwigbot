EarwigBot
=========

EarwigBot_ is a Python bot that edits Wikipedia_ and interacts over IRC_.
This README provides a basic overview of how to install and setup the bot;
more detailed information is located in the ``docs/`` directory
(`available online_`).

History
-------

Development began, based on `Pywikibot`_, in early 2009. Approval for its
first task, a `copyright violation detector`_, was carried out in May, and the
bot has been running consistently ever since. It currently handles
`several ongoing tasks`_ ranging from statistics generation to category
cleanup, and on-demand tasks such as WikiProject template tagging. Since it
started running, the bot has made over 300,000 edits.

The current version of its codebase began development in April 2011, moving
away from Pywikibot to a custom framework.

Installation
------------

This package contains the core ``earwigbot``, abstracted to be usable and
customizable by anyone running a bot on a MediaWiki site. Since it is modular,
the IRC components can be disabled if desired. IRC commands and bot tasks
specific to `my instance of EarwigBot`_ that I don't feel the average user
will need are available from the repository `earwigbot-plugins`_.

Latest release
~~~~~~~~~~~~~~

EarwigBot is available from the `Python Package Index`_, so you can install
the latest release with:

    pip install earwigbot

There are a few sets of optional dependencies:

- ``crypto``: Allows encrypting bot passwords and secrets in the config
- ``sql``: Allows interfacing with MediaWiki databases (e.g. on Toolforge_)
- ``copyvios``: Includes parsing libraries for checking copyright violations
- ``dev``: Installs development dependencies (e.g. test runners)

For example, to install all non-dev dependencies:

    pip install 'earwigbot[crypto,sql,copyvios]'

Errors while pip is installing dependencies may be due to missing header
files. For example, on Ubuntu, see `this StackOverflow post`_.

Development version
~~~~~~~~~~~~~~~~~~~

You can install the development version of the bot::

    git clone https://github.com/earwig/earwigbot.git
    cd earwigbot
    python3 -m venv venv
    . venv/bin/activate
    pip install -e '.[crypto,sql,copyvios,dev]'

To run the bot's unit tests, run ``pytest`` (requires the ``dev``
dependencies). Coverage is currently rather incomplete.

Setup
-----

The bot stores its data in a "working directory", including its config file
and databases. This is also the location where you will place custom IRC
commands and bot tasks, which will be explained later. It doesn't matter where
this directory is, as long as the bot can write to it.

Start the bot with ``earwigbot path/to/working/dir``, or just ``earwigbot`` if
the working directory is the current directory. It will notice that no
``config.yml`` file exists and take you through the setup process.

There is currently no way to edit the ``config.yml`` file from within the bot
after it has been created, but you should be able to make any necessary
changes yourself.

After setup, the bot will start. This means it will connect to the IRC servers
it has been configured for, schedule bot tasks to run at specific times, and
then wait for instructions (as commands on IRC). For a list of commands, say
"``!help``" (commands are messages prefixed with an exclamation mark).

You can stop the bot at any time with Control+C, same as you stop a normal
Python program, and it will try to exit safely. You can also use the
"``!quit``" command on IRC.

Customizing
-----------

The bot's working directory contains a ``commands`` subdirectory and a
``tasks`` subdirectory. Custom IRC commands can be placed in the former,
whereas custom wiki bot tasks go into the latter. Developing custom modules is
explained below, and in more detail through the bot's documentation_ or in the
``docs/`` dir.

Note that custom commands will override built-in commands and tasks with the
same name.

``Bot`` and ``BotConfig``
~~~~~~~~~~~~~~~~~~~~~~~~~

`earwigbot.bot.Bot`_ is EarwigBot's main class. You don't have to instantiate
this yourself, but it's good to be familiar with its attributes and methods,
because it is the main way to communicate with other parts of the bot. A
``Bot`` object is accessible as an attribute of commands and tasks (i.e.,
``self.bot``).

`earwigbot.config.BotConfig`_ stores configuration information for the bot.
Its docstring explains what each attribute is used for, but essentially each
"node" (one of ``config.components``, ``wiki``, ``irc``, ``commands``,
``tasks``, and ``metadata``) maps to a section of the bot's ``config.yml``
file. For example, if ``config.yml`` includes something like::

    irc:
        frontend:
            nick: MyAwesomeBot
            channels:
                - "##earwigbot"
                - "#channel"
                - "#other-channel"

then ``config.irc["frontend"]["nick"]`` will be ``"MyAwesomeBot"`` and
``config.irc["frontend"]["channels"]`` will be ``["##earwigbot", "#channel",
"#other-channel"]``.

Custom IRC commands
~~~~~~~~~~~~~~~~~~~

Custom commands are subclasses of `earwigbot.commands.Command`_ that override
``Command``'s ``process()`` (and optionally ``check()``, ``setup()``, or
``unload()``) methods.

The bot has a wide selection of built-in commands and plugins to act as sample
code and/or to give ideas. Start with test_, and then check out chanops_ and
afc_status_ for some more complicated scripts.

Custom bot tasks
~~~~~~~~~~~~~~~~

Custom tasks are subclasses of `earwigbot.tasks.Task`_ that override
``Task``'s ``run()`` (and optionally ``setup()`` or ``unload()``) methods.

See the built-in wikiproject_tagger_ task for a relatively straightforward
task, or the afc_statistics_ plugin for a more complicated one.

The Wiki Toolset
----------------

EarwigBot's answer to the Pywikibot_ is the Wiki Toolset (``earwigbot.wiki``),
which you will mainly access through ``bot.wiki``.

``bot.wiki`` provides three methods for the management of Sites:
``get_site()``, ``add_site()``, and ``remove_site()``. Sites are objects that
simply represent a MediaWiki site. A single instance of EarwigBot (i.e. a
single *working directory*) is expected to relate to a single site or group of
sites using the same login info (like all WMF wikis with CentralAuth).

Load your default site (the one that you picked during setup) with
``site = bot.wiki.get_site()``.

Not all aspects of the toolset are covered in the docs. Explore `its code and
docstrings`_ to learn how to use it in a more hands-on fashion. For reference,
``bot.wiki`` is an instance of ``earwigbot.wiki.SitesDB`` tied to the
``sites.db`` file in the bot's working directory.

.. _EarwigBot:                      https://en.wikipedia.org/wiki/User:EarwigBot
.. _Wikipedia:                      https://en.wikipedia.org/
.. _IRC:                            https://en.wikipedia.org/wiki/Internet_Relay_Chat
.. _available online:               https://pythonhosted.org/earwigbot/
.. _Pywikibot:                      https://www.mediawiki.org/wiki/Manual:Pywikibot
.. _copyright violation detector:   https://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/EarwigBot_1
.. _several ongoing tasks:          https://en.wikipedia.org/wiki/User:EarwigBot#Tasks
.. _my instance of EarwigBot:       https://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:              https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:           https://pypi.python.org/pypi/earwigbot
.. _Toolforge:                      https://wikitech.wikimedia.org/wiki/Portal:Toolforge
.. _this StackOverflow post:        https://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu/6504860#6504860
.. _documentation:                  https://pythonhosted.org/earwigbot/
.. _earwigbot.bot.Bot:              https://github.com/earwig/earwigbot/blob/main/earwigbot/bot.py
.. _earwigbot.config.BotConfig:     https://github.com/earwig/earwigbot/blob/main/earwigbot/config.py
.. _earwigbot.commands.Command:     https://github.com/earwig/earwigbot/blob/main/earwigbot/commands/__init__.py
.. _test:                           https://github.com/earwig/earwigbot/blob/main/earwigbot/commands/test.py
.. _chanops:                        https://github.com/earwig/earwigbot/blob/main/earwigbot/commands/chanops.py
.. _afc_status:                     https://github.com/earwig/earwigbot-plugins/blob/main/commands/afc_status.py
.. _earwigbot.tasks.Task:           https://github.com/earwig/earwigbot/blob/main/earwigbot/tasks/__init__.py
.. _wikiproject_tagger:             https://github.com/earwig/earwigbot/blob/main/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:                 https://github.com/earwig/earwigbot-plugins/blob/main/tasks/afc_statistics.py
.. _its code and docstrings:        https://github.com/earwig/earwigbot/tree/main/earwigbot/wiki
