Setup
=====

The bot stores its data in a "working directory", including its config file and
databases. This is also the location where you will place custom IRC commands
and bot tasks, which will be explained later. It doesn't matter where this
directory is, as long as the bot can write to it.

Start the bot with :command:`earwigbot path/to/working/dir`, or just
:command:`earwigbot` if the working directory is the current directory. It will
notice that no :file:`config.yml` file exists and take you through the setup
process.

There is currently no way to edit the :file:`config.yml` file from within the
bot after it has been created, but YAML is a very straightforward format, so
you should be able to make any necessary changes yourself. Check out the
`explanation of YAML`_ on Wikipedia for help.

After setup, the bot will start. This means it will connect to the IRC servers
it has been configured for, schedule bot tasks to run at specific times, and
then wait for instructions (as commands on IRC). For a list of commands, say
"``!help``" (commands are messages prefixed with an exclamation mark).

You can stop the bot at any time with :kbd:`Control-c`, same as you stop a
normal Python program, and it will try to exit safely. You can also use the
"``!quit``" command on IRC.

.. _explanation of YAML:            http://en.wikipedia.org/wiki/YAML
