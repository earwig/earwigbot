EarwigBot
=========

EarwigBot_ is a Python_ robot that edits Wikipedia_ and interacts with people
over IRC_. This file provides a basic overview of how to install and setup the
bot; more detailed information is located in the ``docs/`` directory (available
online at PyPI_).

History
-------

Development began, based on the `Pywikipedia framework`_, in early 2009.
Approval for its first task, a `copyright violation detector`_, was carried out
in May, and the bot has been running consistently ever since (with the
exception of Jan/Feb 2011). It currently handles `several ongoing tasks`_
ranging from statistics generation to category cleanup, and on-demand tasks
such as WikiProject template tagging. Since it started running, the bot has
made over 50,000 edits.

A project to rewrite it from scratch began in early April 2011, thus moving
away from the Pywikipedia framework and allowing for less overall code, better
integration between bot parts, and easier maintenance.

Installation
------------

This package contains the core ``earwigbot``, abstracted enough that it should
be usable and customizable by anyone running a bot on a MediaWiki site. Since
it is component-based, the IRC components can be disabled if desired. IRC
commands and bot tasks specific to `my instance of EarwigBot`_ that I don't
feel the average user will need are available from the repository
`earwigbot-plugins`_.

It's recommended to run the bot's unit tests before installing. Run ``python
setup.py test`` from the project's root directory. Note that some
tests require an internet connection, and others may take a while to run.
Coverage is currently rather incomplete.

Latest release (v0.3)
~~~~~~~~~~~~~~~~~~~~~

EarwigBot is available from the `Python Package Index`_, so you can install the
latest release with ``pip install earwigbot`` (`get pip`_).

If you get an error while pip is installing dependencies, you may be missing
some header files. For example, on Ubuntu, see `this StackOverflow post`_.

You can also install it from source [1]_ directly::

    curl -Lo earwigbot.tgz https://github.com/earwig/earwigbot/tarball/v0.3
    tar -xf earwigbot.tgz
    cd earwig-earwigbot-*
    python setup.py install
    cd ..
    rm -r earwigbot.tgz earwig-earwigbot-*

Development version
~~~~~~~~~~~~~~~~~~~

You can install the development version of the bot from ``git`` by using
setuptools's ``develop`` command [1]_, probably on the ``develop`` branch which
contains (usually) working code. ``master`` contains the latest release.
EarwigBot uses `git flow`_, so you're free to browse by tags or by new features
(``feature/*`` branches)::

    git clone git://github.com/earwig/earwigbot.git earwigbot
    cd earwigbot
    python setup.py develop

Setup
-----

The bot stores its data in a "working directory", including its config file and
databases. This is also the location where you will place custom IRC commands
and bot tasks, which will be explained later. It doesn't matter where this
directory is, as long as the bot can write to it.

Start the bot with ``earwigbot path/to/working/dir``, or just ``earwigbot`` if
the working directory is the current directory. It will notice that no
``config.yml`` file exists and take you through the setup process.

There is currently no way to edit the ``config.yml`` file from within the bot
after it has been created, but YAML is a very straightforward format, so you
should be able to make any necessary changes yourself. Check out the
`explanation of YAML`_ on Wikipedia for help.

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
explained below, and in more detail through the bot's documentation on PyPI_
(or in the ``docs/`` dir).

Note that custom commands will override built-in commands and tasks with the
same name.

``Bot`` and ``BotConfig``
~~~~~~~~~~~~~~~~~~~~~~~~~

`earwigbot.bot.Bot`_ is EarwigBot's main class. You don't have to instantiate
this yourself, but it's good to be familiar with its attributes and methods,
because it is the main way to communicate with other parts of the bot. A
``Bot`` object is accessible as an attribute of commands and tasks (i.e.,
``self.bot``).

`earwigbot.config.BotConfig`_ stores configuration information for the bot. Its
docstring explains what each attribute is used for, but essentially each "node"
(one of ``config.components``, ``wiki``, ``irc``, ``commands``, ``tasks``, and
``metadata``) maps to a section of the bot's ``config.yml`` file. For example,
if ``config.yml`` includes something like::

    irc:
        frontend:
            nick: MyAwesomeBot
            channels:
                - "##earwigbot"
                - "#channel"
                - "#other-channel"

...then ``config.irc["frontend"]["nick"]`` will be ``"MyAwesomeBot"`` and
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

Custom tasks are subclasses of `earwigbot.tasks.Task`_ that override ``Task``'s
``run()`` (and optionally ``setup()`` or ``unload()``) methods.

See the built-in wikiproject_tagger_ task for a relatively straightforward
task, or the afc_statistics_ plugin for a more complicated one.

The Wiki Toolset
----------------

EarwigBot's answer to the `Pywikipedia framework`_ is the Wiki Toolset
(``earwigbot.wiki``), which you will mainly access through ``bot.wiki``.

``bot.wiki`` provides three methods for the management of Sites -
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

Footnotes
---------

- Questions, comments, or suggestions about the documentation? `Let me know`_
  so I can improve it for other people.

.. [1] ``python setup.py install``/``develop`` may require root, or use the
       ``--user`` switch to install for the current user only.

.. _EarwigBot:                      http://en.wikipedia.org/wiki/User:EarwigBot
.. _Python:                         http://python.org/
.. _Wikipedia:                      http://en.wikipedia.org/
.. _IRC:                            http://en.wikipedia.org/wiki/Internet_Relay_Chat
.. _PyPI:                           http://packages.python.org/earwigbot
.. _Pywikipedia framework:          http://pywikipediabot.sourceforge.net/
.. _copyright violation detector:   http://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/EarwigBot_1
.. _several ongoing tasks:          http://en.wikipedia.org/wiki/User:EarwigBot#Tasks
.. _my instance of EarwigBot:       http://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:              https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:           https://pypi.python.org/pypi/earwigbot
.. _get pip:                        http://pypi.python.org/pypi/pip
.. _this StackOverflow post:        http://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu/6504860#6504860
.. _git flow:                       http://nvie.com/posts/a-successful-git-branching-model/
.. _explanation of YAML:            http://en.wikipedia.org/wiki/YAML
.. _earwigbot.bot.Bot:              https://github.com/earwig/earwigbot/blob/develop/earwigbot/bot.py
.. _earwigbot.config.BotConfig:     https://github.com/earwig/earwigbot/blob/develop/earwigbot/config.py
.. _earwigbot.commands.Command:     https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/__init__.py
.. _test:                           https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/test.py
.. _chanops:                        https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/chanops.py
.. _afc_status:                     https://github.com/earwig/earwigbot-plugins/blob/develop/commands/afc_status.py
.. _earwigbot.tasks.Task:           https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/__init__.py
.. _wikiproject_tagger:             https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:                 https://github.com/earwig/earwigbot-plugins/blob/develop/tasks/afc_statistics.py
.. _its code and docstrings:        https://github.com/earwig/earwigbot/tree/develop/earwigbot/wiki
.. _Let me know:                    ben.kurtovic@gmail.com
