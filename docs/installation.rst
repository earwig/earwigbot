Installation
============

This package contains the core :py:mod:`earwigbot`, abstracted to be usable
and customizable by anyone running a bot on a MediaWiki site. Since it is
modular, the IRC components can be disabled if desired. IRC commands and bot
tasks specific to `my instance of EarwigBot`_ that I don't feel the average
user will need are available from the repository `earwigbot-plugins`_.

Latest release
--------------

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
-------------------

You can install the development version of the bot::

    git clone https://github.com/earwig/earwigbot.git
    cd earwigbot
    python3 -m venv venv
    . venv/bin/activate
    pip install -e '.[crypto,sql,copyvios,dev]'

To run the bot's unit tests, run :command:`pytest` (requires the ``dev``
dependencies). Coverage is currently rather incomplete.

.. _my instance of EarwigBot: https://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:        https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:     https://pypi.python.org/pypi/earwigbot
.. _Toolforge:                https://wikitech.wikimedia.org/wiki/Portal:Toolforge
.. _this StackOverflow post:  https://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu/6504860#6504860
