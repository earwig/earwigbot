EarwigBot
=========

EarwigBot_ is a Python_ robot that edits Wikipedia_ and interacts with people
over IRC_.

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
commands and bot tasks specific to `my instance of EarwigBot`_ are available
from the package `earwigbot-plugins`_.

Latest release (v0.1)
~~~~~~~~~~~~~~~~~~~~~

EarwigBot is available from the `Python Package Index`_, so you can install the
latest release with ``pip install earwigbot`` (`get pip`_).

You can also install it from source [1]_ directly::

    curl -Lo earwigbot.tgz "https://github.com/earwig/earwigbot/tarball/v0.1"
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

It's recommended to run the bot's unit tests before installing. Run
``python setup.py test`` from the project's root directory.

*Note:* some unit tests require an internet connection.

Customizing
-----------

Hacking
-------

Footnotes
---------

.. _EarwigBot:                    http://en.wikipedia.org/wiki/User:EarwigBot
.. _Python:                       http://python.org/
.. _Wikipedia:                    http://en.wikipedia.org/
.. _IRC:                          http://en.wikipedia.org/wiki/Internet_Relay_Chat
.. _Pywikipedia framework:        http://pywikipediabot.sourceforge.net/
.. _copyright violation detector: http://en.wikipedia.org/wiki/Wikipedia:Bots/Requests_for_approval/EarwigBot_1
.. _several ongoing tasks:        http://en.wikipedia.org/wiki/User:EarwigBot#Tasks
.. _my instance of EarwigBot:     http://en.wikipedia.org/wiki/User:EarwigBot
.. _earwigbot-plugins:            https://github.com/earwig/earwigbot-plugins
.. _Python Package Index:         http://pypi.python.org
.. _get pip:                      http://pypi.python.org/pypi/pip
.. _git flow:                     http://nvie.com/posts/a-successful-git-branching-model/

.. [1] ``python setup.py install``/``develop`` may require root, or use the
       ``--user`` switch to install for the current user only
