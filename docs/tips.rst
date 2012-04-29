Tips
====

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
  tasks without restarting the bot. [1]_ Combined with using the `!git plugin`_
  for pulling repositories from IRC, this can provide a seamless command/task
  development workflow if the bot runs on an external server and you set up
  its working directory as a git repo.

- You can run a task by itself instead of the entire bot with ``earwigbot
  path/to/working/dir --task task_name``.

- Questions, comments, or suggestions about the documentation? `Let me know`_
  so I can improve it for other people.

.. rubric:: Footnotes

.. [1] In reality, all this does is call ``bot.commands.load()`` and
       ``bot.tasks.load()``!

.. _logging:                        http://docs.python.org/library/logging.html
.. _Let me know:                    ben.kurtovic@verizon.net
.. _!git plugin:                    https://github.com/earwig/earwigbot-plugins/blob/develop/commands/git.py
