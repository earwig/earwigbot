Tips
====

- Logging_ is a fantastic way to monitor the bot's progress as it runs. It has
  a slew of built-in loggers, and enabling log retention (so logs are saved to
  :file:`logs/` in the working directory) is highly recommended. In the normal
  setup, there are three log files, each of which "rotate" at a  specific time
  (:file:`filename.log` becomes :file:`filename.log.2012-04-10`, for example).
  The :file:`debug.log` file rotates every hour, and maintains six hours of
  logs of every level (``DEBUG`` and up). :file:`bot.log` rotates every day at
  midnight, and maintains seven days of non-debug logs (``INFO`` and up).
  Finally, :file:`error.log` rotates every Sunday night, and maintains four
  weeks of logs indicating unexpected events (``WARNING`` and up).

  To use logging in your commands or tasks (recommended),
  :py:class:~earwigbot.commands.BaseCommand` and
  :py:class:~earwigbot.tasks.BaseTask` provide :py:attr:`logger` attributes
  configured for the specific command or task. If you're working with other
  classes, :py:attr:`bot.logger` is the root logger
  (:py:obj:`logging.getLogger("earwigbot")` by default), so you can use
  :py:func:`~logging.Logger.getChild` to make your logger. For example, task
  loggers are essentially
  :py:attr:`bot.logger.getChild("tasks").getChild(task.name) <bot.logger>`.

- A very useful IRC command is "``!reload``", which reloads all commands and
  tasks without restarting the bot. [1]_ Combined with using the `!git plugin`_
  for pulling repositories from IRC, this can provide a seamless command/task
  development workflow if the bot runs on an external server and you set up
  its working directory as a git repo.

- You can run a task by itself instead of the entire bot with
  :command:`earwigbot path/to/working/dir --task task_name`.

- Questions, comments, or suggestions about the documentation?
  `Create an issue`_ so I can improve it for other people.

.. rubric:: Footnotes

.. [1] In reality, all this does is call :py:meth:`bot.commands.load()
       <earwigbot.managers._ResourceManager.load>` and
       :py:meth:`bot.tasks.load() <earwigbot.managers._ResourceManager.load>`!

.. _logging:         https://docs.python.org/library/logging.html
.. _!git plugin:     https://github.com/earwig/earwigbot-plugins/blob/develop/commands/git.py
.. _create an issue: https://github.com/earwig/earwigbot/issues
