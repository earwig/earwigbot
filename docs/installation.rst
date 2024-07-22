Installation
============

This package contains the core :py:mod:`earwigbot`, abstracted enough that it
should be usable and customizable by anyone running a bot on a MediaWiki site.
Since it is component-based, the IRC components can be disabled if desired. IRC
commands and bot tasks specific to `my instance of EarwigBot`_ that I don't
feel the average user will need are available from the repository
`earwigbot-plugins`_.

It's recommended to run the bot's unit tests before installing. Run
:command:`python setup.py test` from the project's root directory. Note that
some tests require an internet connection, and others may take a while to run.
Coverage is currently rather incomplete.

Latest release
--------------

EarwigBot is available from the `Python Package Index`_, so you can install the
latest release with :command:`pip install earwigbot`.

If you get an error while pip is installing dependencies, you may be missing
some header files. For example, on Ubuntu, see `this StackOverflow post`_.

Development version
-------------------

You can install the development version of the bot from :command:`git` by using
setuptools's :command:`develop` command::

    git clone git://github.com/earwig/earwigbot.git earwigbot
    cd earwigbot
    python setup.py develop

.. _my instance of EarwigBot: https://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:        https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:     https://pypi.python.org/pypi/earwigbot
.. _this StackOverflow post:  https://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu/6504860#6504860
