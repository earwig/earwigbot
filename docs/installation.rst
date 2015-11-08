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

Latest release (v0.1)
---------------------

EarwigBot is available from the `Python Package Index`_, so you can install the
latest release with :command:`pip install earwigbot` (`get pip`_).

If you get an error while pip is installing dependencies, you may be missing
some header files. For example, on Ubuntu, see `this StackOverflow post`_.

You can also install it from source [1]_ directly::

    curl -Lo earwigbot.tgz https://github.com/earwig/earwigbot/tarball/v0.1
    tar -xf earwigbot.tgz
    cd earwig-earwigbot-*
    python setup.py install
    cd ..
    rm -r earwigbot.tgz earwig-earwigbot-*

Development version
-------------------

You can install the development version of the bot from :command:`git` by using
setuptools's :command:`develop` command [1]_, probably on the ``develop``
branch which contains (usually) working code. ``master`` contains the latest
release. EarwigBot uses `git flow`_, so you're free to browse by tags or by new
features (``feature/*`` branches)::

    git clone git://github.com/earwig/earwigbot.git earwigbot
    cd earwigbot
    python setup.py develop

.. rubric:: Footnotes

.. [1] :command:`python setup.py install`/:command:`develop` may require root,
       or use the :command:`--user` switch to install for the current user
       only.

.. _my instance of EarwigBot: http://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:        https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:     http://pypi.python.org
.. _get pip:                  http://pypi.python.org/pypi/pip
.. _this StackOverflow post:        http://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu/6504860#6504860
.. _git flow:                 http://nvie.com/posts/a-successful-git-branching-model/
