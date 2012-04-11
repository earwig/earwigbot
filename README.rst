EarwigBot
=========

EarwigBot_ is a Python_ robot that edits Wikipedia_ and interacts with people
over IRC_. This file provides a basic overview of how to install and setup the
bot; more detailed information is located in the ``docs/`` directory (available
online at PyPI_).

History
-------

Development began, based on the `Pywikipedia framework`_, in early 2009.
Approval for its fist task, a `copyright violation detector`_, was carried out
in May, and the bot has been running consistently ever since (with the
exception of Jan/Feb 2011). It currently handles `several ongoing tasks`_
ranging from statistics generation to category cleanup, and on-demand tasks
such as WikiProject template tagging. Since it started running, the bot has
made over 50,000 edits.

A project to rewrite it from scratch began in early April 2011, thus moving
away from the Pywikipedia framework and allowing for less overall code, better
integration between bot parts, and easier maintenance. Thanks to abstraction of
the core bot from tasks specific to my instance of it, the bot core can now be
used by other people with little additional work. How to take full advantage of
it is explained below.

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

Latest release (v0.1)
~~~~~~~~~~~~~~~~~~~~~

EarwigBot is available from the `Python Package Index`_, so you can install the
latest release with ``pip install earwigbot`` (`get pip`_).

You can also install it from source [1]_ directly::

    curl -Lo earwigbot.tgz https://github.com/earwig/earwigbot/tarball/v0.1
    tar -xf earwigbot.tgz
    cd earwig-earwigbot-*
    python setup.py install
    cd ..
    rm -r earwigbot.tgz earwig-earwigbot-*

Development version
~~~~~~~~~~~~~~~~~~~

You can install the development version of the bot from ``git`` by using
setuptools/distribute's ``develop`` command [1]_, probably on the ``develop``
branch which contains (usually) working code. ``master`` contains the latest
release. EarwigBot uses `git flow`_, so you're free to
browse by tags or by new features (``feature/*`` branches)::

    git clone git://github.com/earwig/earwigbot.git earwigbot
    cd earwigbot
    python setup.py develop

Setup
-----

The bot stores its data in a "working directory", including its config file and
some databases. This is also the location where you will place custom IRC
commands and bot tasks, which will be explained later. It doesn't matter where
this directory is, as long as the bot can write to it.

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
Python program, and it will exit safely. You can also use the "``!quit``"
command on IRC for the same purpose.

Customizing
-----------

The bot's directory contains a ``commands`` subdirectory and a ``tasks``
subdirectory. Custom IRC commands can be placed in the former, whereas custom
wiki bot tasks go into the latter. Developing custom modules is explained
below, and in more detail through the bot's documentation on PyPI_.

You can easily reload commands and tasks without restarting the bot by using
"``!reload``".

Note that custom commands will override built-in commands and tasks with the
same name.

``Bot`` and ``BotConfig``
~~~~~~~~~~~~~~~~~~~~~~~~~

- ``bot.wiki``: entry into `the Wiki Toolset`_, explained below.

XXX: TODO

Custom IRC commands
~~~~~~~~~~~~~~~~~~~

Custom commands are subclasses of `earwigbot.commands.BaseCommand`_ that
override ``BaseCommand``'s ``process()`` (and optionally ``check()``) methods.

``BaseCommand``'s ``__doc__``-strings should explain what each attribute and
method is for and what they should be overridden with, but these are the
basics:

- Class attribute ``name`` is the name of the command. This must be specified.

- Class attribute ``hooks`` is a list of the "IRC events" that this command
  might respond to. It defaults to ``["msg"]``, but options include
  ``"msg_private"`` (for private messages only), ``"msg_public"`` (for channel
  messages only), and ``"join"`` (for when a user joins a channel). See the
  afc_status_ plugin for a command that responds to other hook types.

- Method ``check()`` is passed a ``Data`` [2]_ object, and should return
  ``True`` if you want to respond to this message, or ``False`` otherwise. The
  default behavior is to return ``True`` only if ``data.is_command`` is
  ``True`` and ``data.command == self.name``, which is suitable for most cases.
  A common, straightforward reason for overriding is if a command has aliases
  (see chanops_ for an example). Note that by returning ``True``, you prevent
  any other commands from responding to this message.

- Method ``process()`` is passed the same ``Data`` object as ``check()``, but
  only if ``check()`` returned ``True``. This is where the bulk of your command
  goes. To respond to IRC messages, there are a number of methods of
  ``BaseCommand`` at your disposal. See the the test_ command for a simple
  example, or look in BaseCommand's ``__init__`` method for the full list.
  The most common ones are ``self.say(chan_or_user, msg)``,
  ``self.reply(data, msg)`` (convenience function; sends a reply to the
  issuer of the command in the channel it was received),
  ``self.action(chan_or_user, msg)``, ``self.notice(chan_or_user, msg)``,
  ``self.join(chan)``, and ``self.part(chan)``.

It's important to name the command class ``Command`` within the file, or else
the bot might not recognize it as a command. The name of the file doesn't
really matter and need not match the command's name, but this is recommended
for readability.

The bot has a wide selection of built-in commands and plugins to act as sample
code and/or to give ideas. Start with test_, and then check out chanops_ and
afc_status_ for some more complicated scripts!

Custom bot tasks
~~~~~~~~~~~~~~~~

Custom tasks are subclasses of `earwigbot.tasks.BaseTask`_ that override
``BaseTask``'s ``run()`` (and optionally ``setup()``) methods.

``BaseTask``'s ``_doc__``-strings should explain what each attribute and method
is for and what they should be overridden with, but these are the basics:

- Class attribute ``name`` is the name of the task. This must be specified.

- Class attribute ``number`` can be used to store an optional "task number",
  possibly for use in edit summaries (to be generated with ``make_summary()``).
  For example, EarwigBot's ``config.wiki["summary"]`` is
  ``"([[WP:BOT|Bot]]; [[User:EarwigBot#Task $1|Task $1]]): $2"``, which the
  task class's ``make_summary(comment)`` method will take and replace ``$1``
  with the task number and ``$2`` with the details of the edit. Additionally,
  ``shutoff_enabled()`` (which checks whether the bot has been told to stop
  on-wiki by checking the content of a particular page) can check a different
  page for each task using similar variables. EarwigBot's
  ``config.wiki["shutoff"]["page"]`` is ``"User:$1/Shutoff/Task $2"``; ``$1``
  is substituted with the bot's username, and ``$2`` is substituted with the
  task number, so, e.g., task #14 checks the page
  ``[[User:EarwigBot/Shutoff/Task 14]].`` If the page's content does *not*
  match ``config.wiki["shutoff"]["disabled"]`` (``"run"`` by default), then
  shutoff is considered to be *enabled* and ``shutoff_enabled()`` will return
  ``True``, indicating the task should not run. If you don't intend to use
  either of these methods, feel free to leave this attribute blank.

- Method ``setup()`` is called *once* with no arguments immediately after the
  task is first loaded. Does nothing by default; treat it like an
  ``__init__()`` if you want (``__init__()`` does things by default and a
  dedicated setup method is easier than asking people to use ``super``).

- Method ``run()`` is called with any number of keyword arguments every time
  the task is executed (by ``bot.tasks.start(task_name, **kwargs)``, usually).
  This is where the bulk of the task's code goes. For interfacing with
  MediaWiki sites, read up on `the Wiki Toolset`_ below.

Tasks have access to ``config.tasks[task_name]`` for config information, which
is a node in ``config.yml`` like every other attribute of ``bot.config``. This
can be used to store, for example, edit summaries, or templates to append to
user talk pages, so that these can be easily changed without modifying the task
itself.

It's important to name the task class ``Task`` within the file, or else the bot
might not recognize it as a task. The name of the file doesn't really matter
and need not match the task's name, but this is recommended for readability.

See the built-in wikiproject_tagger_ task for a relatively straightforward
task, or the afc_statistics_ plugin for a more complicated one.

The Wiki Toolset
~~~~~~~~~~~~~~~~

EarwigBot's answer to the `Pywikipedia framework`_ is the Wiki Toolset
(``earwigbot.wiki``), which you will mainly access through ``bot.wiki``.

XXX: TODO

Tips
----

- Logging_ is a fantastic way to track the bot's progress 

- You can run a task by itself instead of the entire bot with ``earwigbot
  path/to/working/dir --task task_name``.

Footnotes
---------

.. [1] ``python setup.py install``/``develop`` may require root, or use the
       ``--user`` switch to install for the current user only.

.. [2] ``Data`` objects are instances of ``earwigbot.irc.Data`` that contain
       information about a single message sent on IRC. Their useful attributes
       are ``chan`` (channel the message was sent from, equal to ``nick`` if
       it's a private message), ``nick`` (nickname of the sender), ``ident``
       (ident_ of the sender), ``host`` (hostname of the sender), ``msg`` (text
       of the sent message), ``is_command`` (boolean telling whether or not
       this message is a bot command, i.e., whether it is prefixed by ``!``),
       ``command`` (if the message is a command, this is the name of the
       command used), and ``args`` (if the message is a command, this is a list
       of the command arguments - for example, if issuing "``!part ##earwig
       Goodbye guys``", ``args`` will equal ``["##earwig", "Goodbye",
       "guys"]``). Note that not all ``Data`` objects will have all of these
       attributes: ``Data`` objects generated by private messages will, but
       ones generated by joins will only have ``chan``, ``nick``, ``ident``,
       and ``host``.

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
.. _Python Package Index:           http://pypi.python.org
.. _get pip:                        http://pypi.python.org/pypi/pip
.. _git flow:                       http://nvie.com/posts/a-successful-git-branching-model/
.. _explanation of YAML:            http://en.wikipedia.org/wiki/YAML
.. _earwigbot.commands.BaseCommand: https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/__init__.py
.. _afc_status:                     https://github.com/earwig/earwigbot-plugins/blob/develop/commands/afc_status.py
.. _chanops:                        https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/chanops.py
.. _test:                           https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/test.py
.. _earwigbot.tasks.BaseTask:       https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/__init__.py
.. _wikiproject_tagger:             https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:                 https://github.com/earwig/earwigbot-plugins/blob/develop/tasks/afc_statistics.py
.. _logging:                        http://docs.python.org/library/logging.html
.. _ident:                          http://en.wikipedia.org/wiki/Ident
