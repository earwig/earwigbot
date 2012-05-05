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
explained below, and in more detail through the bot's documentation on PyPI_.

Note that custom commands will override built-in commands and tasks with the
same name.

``Bot`` and ``BotConfig``
~~~~~~~~~~~~~~~~~~~~~~~~~

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

- ``bot.wiki``: interface with `the Wiki Toolset`_ (see below).

- Finally, ``bot.restart()`` (restarts IRC components and reloads config,
  commands, and tasks) and ``bot.stop()`` can be used almost anywhere. Both
  take an optional "reason" that will be logged and used as the quit message
  when disconnecting from IRC.

`earwigbot.config.BotConfig`_ stores configuration information for the bot. Its
docstring explains what each attribute is used for, but essentially each "node"
(one of ``config.components``, ``wiki``, ``tasks``, ``irc``, and ``metadata``)
maps to a section of the bot's ``config.yml`` file. For example, if
``config.yml`` includes something like::

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

Custom commands are subclasses of `earwigbot.commands.BaseCommand`_ that
override ``BaseCommand``'s ``process()`` (and optionally ``check()``) methods.

``BaseCommand``'s docstrings should explain what each attribute and method is
for and what they should be overridden with, but these are the basics:

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
afc_status_ for some more complicated scripts.

Custom bot tasks
~~~~~~~~~~~~~~~~

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

Dealing with other sites
~~~~~~~~~~~~~~~~~~~~~~~~

*Skip this section if you're only working with one site.*

If a site is *already known to the bot* (meaning that it is stored in the
``sites.db`` file, which includes just your default wiki at first), you can
load a site with ``site = bot.wiki.get_site(name)``, where ``name`` might be
``"enwiki"`` or ``"frwiktionary"`` (you can also do
``site = bot.wiki.get_site(project="wikipedia", lang="en")``). Recall that not
giving any arguments to ``get_site()`` will return the default site.

``add_site()`` is used to add new sites to the sites database. It may be called
with similar arguments as ``get_site()``, but the difference is important.
``get_site()`` only needs enough information to identify the site in its
database, which is usually just its name; the database stores all other
necessary connection info. With ``add_site()``, you need to provide enough
connection info so the toolset can successfully access the site's API/SQL
databases and store that information for later. That might not be much; for
WMF wikis, you can usually use code like this::

    project, lang = "wikipedia", "es"
    try:
        site = bot.wiki.get_site(project=project, lang=lang)
    except earwigbot.SiteNotFoundError:
        # Load site info from http://es.wikipedia.org/w/api.php:
        site = bot.wiki.add_site(project=project, lang=lang)

This works because EarwigBot assumes that the URL for the site is
``"//{lang}.{project}.org"`` and the API is at ``/w/api.php``; this might
change if you're dealing with non-WMF wikis, where the code might look
something more like::

    project, lang = "mywiki", "it"
    try:
        site = bot.wiki.get_site(project=project, lang=lang)
    except earwigbot.SiteNotFoundError:
        # Load site info from http://mysite.net/mywiki/it/s/api.php:
        base_url = "http://mysite.net/" + project + "/" + lang
        db_name = lang + project + "_p"
        sql = {host: "sql.mysite.net", db: db_name}
        site = bot.wiki.add_site(base_url=base_url, script_path="/s", sql=sql)

``remove_site()`` does the opposite of ``add_site()``: give it a site's name
or a project/lang pair like ``get_site()`` takes, and it'll remove that site
from the sites database.

Sites
~~~~~

``Site`` objects provide the following attributes:

- ``name``: the site's name (or "wikiid"), like ``"enwiki"``
- ``project``: the site's project name, like ``"wikipedia"``
- ``lang``: the site's language code, like ``"en"``
- ``domain``: the site's web domain, like ``"en.wikipedia.org"``

and the following methods:

- ``api_query(**kwargs)``: does an API query with the given keyword arguments
  as params
- ``sql_query(query, params=(), ...)``: does an SQL query and yields its
  results (as a generator)
- ``get_replag()``: returns the estimated database replication lag (if we have
  the site's SQL connection info)
- ``namespace_id_to_name(id, all=False)``: given a namespace ID, returns the
  primary associated namespace name (or a list of all names when ``all`` is
  ``True``)
- ``namespace_name_to_id(name)``: given a namespace name, returns the
  associated namespace ID
- ``get_page(title, follow_redirects=False)``: returns a ``Page`` object for
  the given title (or a ``Category`` object if the page's namespace is
  "``Category:``")
- ``get_category(catname, follow_redirects=False)``: returns a ``Category``
  object for the given title (sans namespace)
- ``get_user(username)``: returns a ``User`` object for the given username

Pages (and Categories)
~~~~~~~~~~~~~~~~~~~~~~

Create ``Page`` objects with ``site.get_page(title)``,
``page.toggle_talk()``, ``user.get_userpage()``, or ``user.get_talkpage()``.
They provide the following attributes:

- ``title``: the page's title, or pagename
- ``exists``: whether the page exists
- ``pageid``: an integer ID representing the page
- ``url``: the page's URL
- ``namespace``: the page's namespace as an integer
- ``protection``: the page's current protection status
- ``is_talkpage``: ``True`` if the page is a talkpage, else ``False``
- ``is_redirect``: ``True`` if the page is a redirect, else ``False``

and the following methods:

- ``reload()``: forcibly reload the page's attributes (emphasis on *reload* -
  this is only necessary if there is reason to believe they have changed)
- ``toggle_talk(...)``: returns a content page's talk page, or vice versa
- ``get()``: returns page content
- ``get_redirect_target()``: if the page is a redirect, returns its destination
- ``get_creator()``: returns a ``User`` object representing the first user to
  edit the page
- ``edit(text, summary, minor=False, bot=True, force=False)``: replaces the
  page's content with ``text`` or creates a new page
- ``add_section(text, title, minor=False, bot=True, force=False)``: adds a new
  section named ``title`` at the bottom of the page
- ``copyvio_check(...)``: checks the page for copyright violations
- ``copyvio_compare(url, ...)``: checks the page like ``copyvio_check()``, but
  against a specific URL

Additionally, ``Category`` objects (created with ``site.get_category(name)`` or
``site.get_page(title)`` where ``title`` is in the ``Category:`` namespace)
provide the following additional method:

- ``get_members(use_sql=False, limit=None)``: returns a list of page titles in
  the category (limit is ``50`` by default if using the API)

Users
~~~~~

Create ``User`` objects with ``site.get_user(name)`` or
``page.get_creator()``. They provide the following attributes:

- ``name``: the user's username
- ``exists``: ``True`` if the user exists, or ``False`` if they do not
- ``userid``: an integer ID representing the user
- ``blockinfo``: information about any current blocks on the user (``False`` if
  no block, or a dict of ``{"by": blocking_user, "reason": block_reason,
  "expiry": block_expire_time}``)
- ``groups``: a list of the user's groups
- ``rights``: a list of the user's rights
- ``editcount``: the number of edits made by the user
- ``registration``: the time the user registered as a ``time.struct_time``
- ``emailable``: ``True`` if you can email the user, ``False`` if you cannot
- ``gender``: the user's gender (``"male"``, ``"female"``, or ``"unknown"``)

and the following methods:

- ``reload()``: forcibly reload the user's attributes (emphasis on *reload* -
  this is only necessary if there is reason to believe they have changed)
- ``get_userpage()``: returns a ``Page`` object representing the user's
  userpage
- ``get_talkpage()``: returns a ``Page`` object representing the user's
  talkpage

Additional features
~~~~~~~~~~~~~~~~~~~

Not all aspects of the toolset are covered here. Explore `its code and
docstrings`_ to learn how to use it in a more hands-on fashion. For reference,
``bot.wiki`` is an instance of ``earwigbot.wiki.SitesDB`` tied to the
``sites.db`` file in the bot's working directory.

Tips
----

- Logging_ is a fantastic way to monitor the bot's progress as it runs. It has
  a slew of built-in loggers, and enabling log retention (so logs are saved to
  ``logs/`` in the working directory) is highly recommended. In the normal
  setup, there are three log files, each of which "rotate" at a  specific time
  (``filename.log`` becomes ``filename.log.2012-04-10``, for example). The
  ``debug.log`` file rotates every hour, and maintains six hours of logs of
  every level (``DEBUG`` and up). ``bot.log`` rotates every day at midnight,
  and maintains seven days of non-debug logs (``INFO`` and up). Finally,
  ``error.log`` rotates every Sunday night, and maintains four weeks of logs
  indicating unexpected events (``WARNING`` and up).

  To use logging in your commands or tasks (recommended), ``BaseCommand`` and
  ``BaseTask`` provide ``logger`` attributes configured for the specific
  command or task. If you're working with other classes, ``bot.logger`` is the
  root logger (``logging.getLogger("earwigbot")`` by default), so you can use
  ``getChild`` to make your logger. For example, task loggers are essentially
  ``bot.logger.getChild("tasks").getChild(task.name)``.

- A very useful IRC command is "``!reload``", which reloads all commands and
  tasks without restarting the bot. [3]_ Combined with using the `!git plugin`_
  for pulling repositories from IRC, this can provide a seamless command/task
  development workflow if the bot runs on an external server and you set up
  its working directory as a git repo.

- You can run a task by itself instead of the entire bot with ``earwigbot
  path/to/working/dir --task task_name``.

- Questions, comments, or suggestions about the documentation? `Let me know`_
  so I can improve it for other people.

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

.. [3] In reality, all this does is call ``bot.commands.load()`` and
       ``bot.tasks.load()``!

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
.. _earwigbot.bot.Bot:              https://github.com/earwig/earwigbot/blob/develop/earwigbot/bot.py
.. _earwigbot.config.BotConfig:     https://github.com/earwig/earwigbot/blob/develop/earwigbot/config.py
.. _earwigbot.commands.BaseCommand: https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/__init__.py
.. _afc_status:                     https://github.com/earwig/earwigbot-plugins/blob/develop/commands/afc_status.py
.. _chanops:                        https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/chanops.py
.. _test:                           https://github.com/earwig/earwigbot/blob/develop/earwigbot/commands/test.py
.. _earwigbot.tasks.BaseTask:       https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/__init__.py
.. _wikiproject_tagger:             https://github.com/earwig/earwigbot/blob/develop/earwigbot/tasks/wikiproject_tagger.py
.. _afc_statistics:                 https://github.com/earwig/earwigbot-plugins/blob/develop/tasks/afc_statistics.py
.. _its code and docstrings:        https://github.com/earwig/earwigbot/tree/develop/earwigbot/wiki
.. _logging:                        http://docs.python.org/library/logging.html
.. _Let me know:                    ben.kurtovic@verizon.net
.. _!git plugin:                    https://github.com/earwig/earwigbot-plugins/blob/develop/commands/git.py
.. _ident:                          http://en.wikipedia.org/wiki/Ident
