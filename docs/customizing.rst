Customizing
===========

The bot's working directory contains a :file:`commands` subdirectory and a
:file:`tasks` subdirectory. Custom IRC commands can be placed in the former,
whereas custom wiki bot tasks go into the latter. Developing custom modules is
explained in detail in this documentation.

Note that custom commands will override built-in commands and tasks with the
same name.

:py:class:`~earwigbot.bot.Bot` and :py:class:`~earwigbot.bot.BotConfig`
-----------------------------------------------------------------------

:py:class:`earwigbot.bot.Bot` is EarwigBot's main class. You don't have to
instantiate this yourself, but it's good to be familiar with its attributes and
methods, because it is the main way to communicate with other parts of the bot.
A :py:class:`~earwigbot.bot.Bot` object is accessible as an attribute of
commands and tasks (i.e., :py:attr:`self.bot`).

The most useful attributes are:

- :py:attr:`~earwigbot.bot.Bot.config`: an instance of
  :py:class:`~earwigbot.bot.BotConfig`, for accessing the bot's configuration
  data (see below).

- :py:attr:`~earwigbot.bot.Bot.commands`: the bot's
  :py:class:`~earwigbot.managers.CommandManager`, which is used internally to
  run IRC commands (through :py:meth:`bot.commands.call`, which you shouldn't
  have to use); you can safely reload all commands with
  :py:meth:`~earwigbot.bot.Bot.commands.load`.

- :py:attr:`~earwigbot.bot.Bot.tasks`: the bot's
  :py:class:`~earwigbot.managers.TaskManager`, which can be used to start tasks
  with :py:attr:`~earwigbot.bot.Bot.tasks.start(task_name, **kwargs)`.
  :py:meth:`~earwigbot.bot.Bot.tasks.load` can be used to safely reload all
  tasks.

- :py:attr:`~earwigbot.bot.Bot.frontend` /
  :py:attr:`~earwigbot.bot.Bot.watcher`: instances of
  :py:class:`earwigbot.irc.Frontend` and :py:class:`earwigbot.irc.Watcher`,
  respectively, which represent the bot's connections to these two servers; you
  can, for example, send a message to the frontend with
  :py:attr:`~earwigbot.bot.Bot.frontend.say(chan, msg)` (more on communicating
  with IRC below).

- :py:attr:`~earwigbot.bot.Bot.wiki`: interface with the
  :doc:`Wiki Toolset <toolset>`.

- Finally, :py:meth:`~earwigbot.bot.Bot.restart` (restarts IRC components and
  reloads config, commands, and tasks) and :py:meth:`~earwigbot.bot.Bot.stop`
  can be used almost anywhere. Both take an optional "reason" that will be
  logged and used as the quit message when disconnecting from IRC.

:py:class:`earwigbot.config.BotConfig` stores configuration information for the
bot. Its docstring explains what each attribute is used for, but essentially
each "node" (one of :py:attr:`config.components`, :py:attr:`wiki`,
:py:attr:`tasks`, :py:attr:`tasks`, or :py:attr:`metadata`) maps to a section
of the bot's :file:`config.yml` file. For example, if :file:`config.yml`
includes something like::

    irc:
        frontend:
            nick: MyAwesomeBot
            channels:
                - "##earwigbot"
                - "#channel"
                - "#other-channel"

...then :py:attr:`config.irc["frontend"]["nick"]` will be ``"MyAwesomeBot"``
and :py:attr:`config.irc["frontend"]["channels"]` will be
``["##earwigbot", "#channel", "#other-channel"]``.

Custom IRC commands
-------------------

Custom commands are subclasses of :py:class:`earwigbot.commands.BaseCommand`
that override :py:class:`~earwigbot.commands.BaseCommand`'s
:py:meth:`~earwigbot.commands.BaseCommand.process` (and optionally
:py:meth:`~earwigbot.commands.BaseCommand.check`) methods.

:py:class:`~earwigbot.commands.BaseCommand`'s docstrings should explain what
each attribute and method is for and what they should be overridden with, but
these are the basics:

- Class attribute :py:attr:`~earwigbot.commands.BaseCommand.name` is the name
  of the command. This must be specified.

- Class attribute :py:attr:`~earwigbot.commands.BaseCommand.hooks` is a list of
  the "IRC events" that this command might respond to. It defaults to
  ``["msg"]``, but options include ``"msg_private"`` (for private messages
  only), ``"msg_public"`` (for channel messages only), and ``"join"`` (for when
  a user joins a channel). See the afc_status_ plugin for a command that
  responds to other hook types.

- Method :py:meth:`~earwigbot.commands.BaseCommand.check` is passed a
  :py:class:`~earwigbot.irc.Data` [1]_ object, and should return ``True`` if
  you want to respond to this message, or ``False`` otherwise. The default
  behavior is to return ``True`` only if
  :py:attr:`data.is_command` is ``True`` and :py:attr:`data.command` ==
  :py:attr:`~earwigbot.commands.BaseCommand.name`, which is suitable for most
  cases. A common, straightforward reason for overriding is if a command has
  aliases (see chanops_ for an example). Note that by returning ``True``, you
  prevent any other commands from responding to this message.

- Method :py:meth:`~earwigbot.commands.BaseCommand.process` is passed the same
  :py:class:`~earwigbot.irc.Data` object as
  :py:meth:`~earwigbot.commands.BaseCommand.check`, but only if
  :py:meth:`~earwigbot.commands.BaseCommand.check` returned ``True``. This is
  where the bulk of your command goes. To respond to IRC messages, there are a
  number of methods of :py:class:`~earwigbot.commands.BaseCommand` at your
  disposal. See the the test_ command for a simple example, or look in
  :py:class:`~earwigbot.commands.BaseCommand`'s
  :py:meth:`~earwigbot.commands.BaseCommand.__init__` method for the full list.

  The most common ones are :py:attr:`self.say(chan_or_user, msg)`,
  :py:attr:`self.reply(data, msg)` (convenience function; sends a reply to the
  issuer of the command in the channel it was received),
  :py:attr:`self.action(chan_or_user, msg)`,
  :py:attr:`self.notice(chan_or_user, msg)`, :py:attr:`self.join(chan)`, and
  :py:attr:`self.part(chan)`.

It's important to name the command class :py:class:`Command` within the file,
or else the bot might not recognize it as a command. The name of the file
doesn't really matter and need not match the command's name, but this is
recommended for readability.

The bot has a wide selection of built-in commands and plugins to act as sample
code and/or to give ideas. Start with test_, and then check out chanops_ and
afc_status_ for some more complicated scripts.

Custom bot tasks
----------------

Custom tasks are subclasses of :py:class:`earwigbot.tasks.BaseTask` that
override :py:class:`~earwigbot.tasks.BaseTask`'s
:py:meth:`~earwigbot.tasks.BaseTask.run` (and optionally
:py:meth:`~earwigbot.tasks.BaseTask.setup`) methods.

:py:class:`~earwigbot.tasks.BaseTask`'s docstrings should explain what each
attribute and method is for and what they should be overridden with, but these
are the basics:

- Class attribute :py:attr:`~earwigbot.tasks.BaseTask.name` is the name of the
  task. This must be specified.

- Class attribute :py:attr:`~earwigbot.tasks.BaseTask.number` can be used to
  store an optional "task number", possibly for use in edit summaries (to be
  generated with :py:meth:`~earwigbot.tasks.BaseTask.make_summary`). For
  example, EarwigBot's :py:attr:`config.wiki["summary"]` is
  ``"([[WP:BOT|Bot]]; [[User:EarwigBot#Task $1|Task $1]]): $2"``, which the
  task class's :py:attr:`~earwigbot.tasks.BaseTask.make_summary(comment)`
  method will take and replace ``$1`` with the task number and ``$2`` with the
  details of the edit.
  
  Additionally, :py:meth:`~earwigbot.tasks.BaseTask.shutoff_enabled` (which
  checks whether the bot has been told to stop on-wiki by checking the content
  of a particular page) can check a different page for each task using similar
  variables. EarwigBot's :py:attr:`config.wiki["shutoff"]["page"]` is
  ``"User:$1/Shutoff/Task $2"``; ``$1`` is substituted with the bot's username,
  and ``$2`` is substituted with the task number, so, e.g., task #14 checks the
  page ``[[User:EarwigBot/Shutoff/Task 14]].`` If the page's content does *not*
  match :py:attr:`config.wiki["shutoff"]["disabled"]` (``"run"`` by default),
  then shutoff is considered to be *enabled* and
  :py:meth:`~earwigbot.tasks.BaseTask.shutoff_enabled` will return ``True``,
  indicating the task should not run. If you don't intend to use either of
  these methods, feel free to leave this attribute blank.

- Method :py:meth:`~earwigbot.tasks.BaseTask.setup` is called *once* with no
  arguments immediately after the task is first loaded. Does nothing by
  default; treat it like an :py:meth:`__init__` if you want
  (:py:meth:`~earwigbot.tasks.BaseTask.__init__` does things by default and a
  dedicated setup method is often easier than overriding
  :py:meth:`~earwigbot.tasks.BaseTask.__init__` and using :py:obj:`super`).

- Method :py:meth:`~earwigbot.tasks.BaseTask.run` is called with any number of
  keyword arguments every time the task is executed (by
  :py:attr:`bot.tasks.start(task_name, **kwargs)`, usually). This is where the
  bulk of the task's code goes. For interfacing with MediaWiki sites, read up
  on the :doc:`Wiki Toolset <toolset>`.

Tasks have access to :py:attr:`config.tasks[task_name]` for config information,
which is a node in :file:`config.yml` like every other attribute of
:py:attr:`bot.config`. This can be used to store, for example, edit summaries,
or templates to append to user talk pages, so that these can be easily changed
without modifying the task itself.

It's important to name the task class :py:class:`Task` within the file, or else
the bot might not recognize it as a task. The name of the file doesn't really
matter and need not match the task's name, but this is recommended for
readability.

See the built-in wikiproject_tagger_ task for a relatively straightforward
task, or the afc_statistics_ plugin for a more complicated one.

.. rubric:: Footnotes

.. [1] :py:class:`~earwigbot.irc.Data` objects are instances of
       :py:class:`earwigbot.irc.Data` that contain information about a single
       message sent on IRC. Their useful attributes are
       :py:attr:`~earwigbot.irc.Data.chan` (channel the message was sent from,
       equal to :py:attr:`~earwigbot.irc.Data.nick` if it's a private message),
       :py:attr:`~earwigbot.irc.Data.nick` (nickname of the sender),
       :py:attr:`~earwigbot.irc.Data.ident` (ident_ of the sender),
       :py:attr:`~earwigbot.irc.Data.host` (hostname of the sender),
       :py:attr:`~earwigbot.irc.Data.msg` (text of the sent message),
       :py:attr:`~earwigbot.irc.Data.is_command` (boolean telling whether or
       not this message is a bot command, e.g., whether it is prefixed by
       ``!``), :py:attr:`~earwigbot.irc.Data.command` (if the message is a
       command, this is the name of the command used), and
       :py:attr:`~earwigbot.irc.Data.args` (if the message is a command, this
       is a list of the command arguments - for example, if issuing
       "``!part ##earwig Goodbye guys``", :py:attr:`~earwigbot.irc.Data.args`
       will equal ``["##earwig", "Goodbye", "guys"]``). Note that not all
       :py:class:`~earwigbot.irc.Data` objects will have all of these
       attributes: :py:class:`~earwigbot.irc.Data` objects generated by private
       messages will, but ones generated by joins will only have
       :py:attr:`~earwigbot.irc.Data.chan`,
       :py:attr:`~earwigbot.irc.Data.nick`,
       :py:attr:`~earwigbot.irc.Data.ident`,
       and :py:attr:`~earwigbot.irc.Data.host`.

.. _afc_status:         https://github.com/earwig/earwigbot-plugins/blob/develop/commands/afc_status.py
.. _chanops:            https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/chanops.py
.. _test:               https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/test.py
.. _wikiproject_tagger: https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:     https://github.com/earwig/earwigbot-plugins/blob/develop/tasks/afc_statistics.py
.. _ident:              http://en.wikipedia.org/wiki/Ident
