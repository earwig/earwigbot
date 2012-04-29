Customizing
===========

The bot's working directory contains a ``commands`` subdirectory and a
``tasks`` subdirectory. Custom IRC commands can be placed in the former,
whereas custom wiki bot tasks go into the latter. Developing custom modules is
explained in detail in this documentation.

Note that custom commands will override built-in commands and tasks with the
same name.

``Bot`` and ``BotConfig``
-------------------------

`earwigbot.bot.Bot`_ is EarwigBot's main class. You don't have to instantiate
this yourself, but it's good to be familiar with its attributes and methods,
because it is the main way to communicate with other parts of the bot. A
``Bot`` object is accessible as an attribute of commands and tasks (i.e.,
``self.bot``).

The most useful attributes are:

- ``bot.config``: an instance of ``BotConfig``, for accessing the bot's
  configuration data (see below).

- ``bot.commands``: the bot's ``CommandManager``, which is used internally to
  run IRC commands (through ``bot.commands.call()``, which you shouldn't have
  to use); you can safely reload all commands with  ``bot.commands.load()``.

- ``bot.tasks``: the bot's ``TaskManager``, which can be used to start tasks
  with ``bot.tasks.start(task_name, **kwargs)``. ``bot.tasks.load()`` can be
  used to safely reload all tasks.

- ``bot.frontend`` / ``bot.watcher``: instances of ``earwigbot.irc.Frontend``
  and ``earwigbot.irc.Watcher``, respectively, which represent the bot's
  connections to these two servers; you can, for example, send a message to the
  frontend with ``bot.frontend.say(chan, msg)`` (more on communicating with IRC
  below).

- ``bot.wiki``: interface with the :doc:`Wiki Toolset <toolset>`.

- Finally, ``bot.restart()`` (restarts IRC components and reloads config,
  commands, and tasks) and ``bot.stop()`` can be used almost anywhere. Both
  take an optional "reason" that will be logged and used as the quit message
  when disconnecting from IRC.

`earwigbot.config.BotConfig`_ stores configuration information for the bot. Its
``__doc__``string explains what each attribute is used for, but essentially
each "node" (one of ``config.components``, ``wiki``, ``tasks``, ``irc``, or
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
-------------------

Custom commands are subclasses of `earwigbot.commands.BaseCommand`_ that
override ``BaseCommand``'s ``process()`` (and optionally ``check()``) methods.

``BaseCommand``'s docstrings should explain what each attribute andmethod is
for and what they should be overridden with, but these are the basics:

- Class attribute ``name`` is the name of the command. This must be specified.

- Class attribute ``hooks`` is a list of the "IRC events" that this command
  might respond to. It defaults to ``["msg"]``, but options include
  ``"msg_private"`` (for private messages only), ``"msg_public"`` (for channel
  messages only), and ``"join"`` (for when a user joins a channel). See the
  afc_status_ plugin for a command that responds to other hook types.

- Method ``check()`` is passed a ``Data`` [1]_ object, and should return
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
afc_status_ for some more complicated scripts.

Custom bot tasks
----------------

Custom tasks are subclasses of `earwigbot.tasks.BaseTask`_ that override
``BaseTask``'s ``run()`` (and optionally ``setup()``) methods.

``BaseTask``'s docstrings should explain what each attribute and method is for
and what they should be overridden with, but these are the basics:

- Class attribute ``name`` is the name of the task. This must be specified.

- Class attribute ``number`` can be used to store an optional "task number",
  possibly for use in edit summaries (to be generated with ``make_summary()``).
  For example, EarwigBot's ``config.wiki["summary"]`` is
  ``"([[WP:BOT|Bot]]; [[User:EarwigBot#Task $1|Task $1]]): $2"``, which the
  task class's ``make_summary(comment)`` method will take and replace ``$1``
  with the task number and ``$2`` with the details of the edit.
  
  Additionally, ``shutoff_enabled()`` (which checks whether the bot has been
  told to stop on-wiki by checking the content of a particular page) can check
  a different page for each task using similar variables. EarwigBot's
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
  dedicated setup method is often easier than overriding ``__init__()`` and
  using ``super``).

- Method ``run()`` is called with any number of keyword arguments every time
  the task is executed (by ``bot.tasks.start(task_name, **kwargs)``, usually).
  This is where the bulk of the task's code goes. For interfacing with
  MediaWiki sites, read up on the :doc:`Wiki Toolset <toolset>`.

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

.. rubric:: Footnotes

.. [1] ``Data`` objects are instances of ``earwigbot.irc.Data`` that contain
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

.. _earwigbot.bot.Bot:              https://github.com/earwig/earwigbot/blob/develop/earwigbot/bot.py
.. _earwigbot.config.BotConfig:     https://github.com/earwig/earwigbot/blob/develop/earwigbot/config.py
.. _earwigbot.commands.BaseCommand: https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/__init__.py
.. _afc_status:                     https://github.com/earwig/earwigbot-plugins/blob/develop/commands/afc_status.py
.. _chanops:                        https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/chanops.py
.. _test:                           https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/test.py
.. _earwigbot.tasks.BaseTask:       https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/__init__.py
.. _wikiproject_tagger:             https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:                 https://github.com/earwig/earwigbot-plugins/blob/develop/tasks/afc_statistics.py
.. _ident:                          http://en.wikipedia.org/wiki/Ident
