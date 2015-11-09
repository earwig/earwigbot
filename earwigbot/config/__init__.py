# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2015 Ben Kurtovic <ben.kurtovic@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from collections import OrderedDict
from getpass import getpass
from hashlib import sha256
import logging
import logging.handlers
from os import mkdir, path
import stat

import yaml

from earwigbot import importer
from earwigbot.config.formatter import BotFormatter
from earwigbot.config.node import ConfigNode
from earwigbot.config.ordered_yaml import OrderedLoader
from earwigbot.config.permissions import PermissionsDB
from earwigbot.config.script import ConfigScript
from earwigbot.exceptions import NoConfigError

Blowfish = importer.new("Crypto.Cipher.Blowfish")
bcrypt = importer.new("bcrypt")

__all__ = ["BotConfig"]

class BotConfig(object):
    """
    **EarwigBot: YAML Config File Manager**

    This handles all tasks involving reading and writing to our config file,
    including encrypting and decrypting passwords and making a new config file
    from scratch at the inital bot run.

    BotConfig has a few attributes and methods, including the following:

    - :py:attr:`root_dir`:   bot's working directory; contains
      :file:`config.yml`, :file:`logs/`
    - :py:attr:`path`:       path to the bot's config file
    - :py:attr:`components`: enabled components
    - :py:attr:`wiki`:       information about wiki-editing
    - :py:attr:`irc`:        information about IRC
    - :py:attr:`commands`:   information about IRC commands
    - :py:attr:`tasks`:      information for bot tasks
    - :py:attr:`metadata`:   miscellaneous information
    - :py:meth:`schedule`:   tasks scheduled to run at a given time

    BotConfig also has some methods used in config loading:

    - :py:meth:`load`:    loads (or reloads) and parses our config file
    - :py:meth:`decrypt`: decrypts an object in the config tree
    """

    def __init__(self, bot, root_dir, level):
        self._bot = bot
        self._root_dir = root_dir
        self._logging_level = level
        self._config_path = path.join(self.root_dir, "config.yml")
        self._log_dir = path.join(self.root_dir, "logs")
        perms_file = path.join(self.root_dir, "permissions.db")
        self._permissions = PermissionsDB(perms_file)
        self._decryption_cipher = None
        self._data = None

        self._components = ConfigNode()
        self._wiki = ConfigNode()
        self._irc = ConfigNode()
        self._commands = ConfigNode()
        self._tasks = ConfigNode()
        self._metadata = ConfigNode()

        self._nodes = [self._components, self._wiki, self._irc, self._commands,
                       self._tasks, self._metadata]

        self._decryptable_nodes = [  # Default nodes to decrypt
            (self._wiki, ("password",)),
            (self._wiki, ("search", "credentials", "key")),
            (self._wiki, ("search", "credentials", "secret")),
            (self._irc, ("frontend", "nickservPassword")),
            (self._irc, ("watcher", "nickservPassword")),
        ]

    def __repr__(self):
        """Return the canonical string representation of the BotConfig."""
        res = "BotConfig(root_dir={0!r}, level={1!r})"
        return res.format(self.root_dir, self.logging_level)

    def __str__(self):
        """Return a nice string representation of the BotConfig."""
        return "<BotConfig at {0}>".format(self.root_dir)

    def _handle_missing_config(self):
        print "Config file missing or empty:", self._config_path
        msg = "Would you like to create a config file now? [Y/n] "
        choice = raw_input(msg)
        if choice.lower().startswith("n"):
            raise NoConfigError()
        else:
            try:
                ConfigScript(self).make_new()
            except KeyboardInterrupt:
                raise NoConfigError()

    def _load(self):
        """Load data from our JSON config file (config.yml) into self._data."""
        filename = self._config_path
        with open(filename, 'r') as fp:
            try:
                self._data = yaml.load(fp, OrderedLoader)
            except yaml.YAMLError:
                print "Error parsing config file {0}:".format(filename)
                raise

    def _setup_logging(self):
        """Configures the logging module so it works the way we want it to."""
        log_dir = self._log_dir
        logger = logging.getLogger("earwigbot")
        logger.handlers = []  # Remove any handlers already attached to us
        logger.setLevel(logging.DEBUG)
        color_formatter = BotFormatter(color=True)
        formatter = BotFormatter()

        if self.metadata.get("enableLogging"):
            hand = logging.handlers.TimedRotatingFileHandler
            logfile = lambda f: path.join(log_dir, f)

            if not path.isdir(log_dir):
                if not path.exists(log_dir):
                    mkdir(log_dir, stat.S_IWUSR|stat.S_IRUSR|stat.S_IXUSR)
                else:
                    msg = "log_dir ({0}) exists but is not a directory!"
                    print msg.format(log_dir)
                    return

            main_handler = hand(logfile("bot.log"), "midnight", 1, 7)
            error_handler = hand(logfile("error.log"), "W6", 1, 4)
            debug_handler = hand(logfile("debug.log"), "H", 1, 6)

            main_handler.setLevel(logging.INFO)
            error_handler.setLevel(logging.WARNING)
            debug_handler.setLevel(logging.DEBUG)

            for h in (main_handler, error_handler, debug_handler):
                h.setFormatter(formatter)
                logger.addHandler(h)

        self._stream_handler = stream = logging.StreamHandler()
        stream.setLevel(self._logging_level)
        stream.setFormatter(color_formatter)
        logger.addHandler(stream)

    def _decrypt(self, node, nodes):
        """Try to decrypt the contents of a config node. Use self.decrypt()."""
        try:
            node._decrypt(self._decryption_cipher, nodes[:-1], nodes[-1])
        except ValueError:
            print "Error decrypting passwords:"
            raise

    @property
    def bot(self):
        """The config's Bot object."""
        return self._bot

    @property
    def root_dir(self):
        """The bot's root directory containing its config file and more."""
        return self._root_dir

    @property
    def logging_level(self):
        """The minimum logging level for messages logged via stdout."""
        return self._logging_level

    @logging_level.setter
    def logging_level(self, level):
        self._logging_level = level
        self._stream_handler.setLevel(level)

    @property
    def path(self):
        """The path to the bot's config file."""
        return self._config_path

    @property
    def log_dir(self):
        """The directory containing the bot's logs."""
        return self._log_dir

    @property
    def data(self):
        """The entire config file as a decoded JSON object."""
        return self._data

    @property
    def components(self):
        """A dict of enabled components."""
        return self._components

    @property
    def wiki(self):
        """A dict of information about wiki-editing."""
        return self._wiki

    @property
    def irc(self):
        """A dict of information about IRC."""
        return self._irc

    @property
    def commands(self):
        """A dict of information for IRC commands."""
        return self._commands

    @property
    def tasks(self):
        """A dict of information for bot tasks."""
        return self._tasks

    @property
    def metadata(self):
        """A dict of miscellaneous information."""
        return self._metadata

    def is_loaded(self):
        """Return ``True`` if our config file has been loaded, or ``False``."""
        return self._data is not None

    def is_encrypted(self):
        """Return ``True`` if passwords are encrypted, otherwise ``False``."""
        return self.metadata.get("encryptPasswords", False)

    def load(self):
        """Load, or reload, our config file.

        First, check if we have a valid config file, and if not, notify the
        user. If there is no config file at all, offer to make one, otherwise
        exit.

        Data from the config file is stored in six
        :py:class:`~earwigbot.config.ConfigNode`\ s (:py:attr:`components`,
        :py:attr:`wiki`, :py:attr:`irc`, :py:attr:`commands`, :py:attr:`tasks`,
        :py:attr:`metadata`) for easy access (as well as the lower-level
        :py:attr:`data` attribute). If passwords are encrypted, we'll use
        :py:func:`~getpass.getpass` for the key and then decrypt them. If the
        config is being reloaded, encrypted items will be automatically
        decrypted if they were decrypted earlier.
        """
        if not path.exists(self._config_path):
            self._handle_missing_config()
        self._load()
        if not self._data:
            self._handle_missing_config()
            self._load()

        self.components._load(self._data.get("components", OrderedDict()))
        self.wiki._load(self._data.get("wiki", OrderedDict()))
        self.irc._load(self._data.get("irc", OrderedDict()))
        self.commands._load(self._data.get("commands", OrderedDict()))
        self.tasks._load(self._data.get("tasks", OrderedDict()))
        self.metadata._load(self._data.get("metadata", OrderedDict()))

        self._setup_logging()
        if self.is_encrypted():
            if not self._decryption_cipher:
                try:
                    blowfish_new = Blowfish.new
                    hashpw = bcrypt.hashpw
                except ImportError:
                    url1 = "http://www.mindrot.org/projects/py-bcrypt"
                    url2 = "https://www.dlitz.net/software/pycrypto/"
                    e = "Encryption requires the 'py-bcrypt' and 'pycrypto' packages: {0}, {1}"
                    raise NoConfigError(e.format(url1, url2))
                key = getpass("Enter key to decrypt bot passwords: ")
                self._decryption_cipher = blowfish_new(sha256(key).digest())
                signature = self.metadata["signature"]
                if hashpw(key, signature) != signature:
                    raise RuntimeError("Incorrect password.")
            for node, nodes in self._decryptable_nodes:
                self._decrypt(node, nodes)

        if self.irc:
            self.irc["permissions"] = self._permissions
            self._permissions.load()

    def decrypt(self, node, *nodes):
        """Decrypt an object in our config tree.

        :py:attr:`_decryption_cipher` is used as our key, retrieved using
        :py:func:`~getpass.getpass` in :py:meth:`load` if it wasn't already
        specified. If this is called when passwords are not encrypted (check
        with :py:meth:`is_encrypted`), nothing will happen. We'll also keep
        track of this node if :py:meth:`load` is called again (i.e. to reload)
        and automatically decrypt it.

        Example usage::

            >>> config.decrypt(config.irc, "frontend", "nickservPassword")
            # decrypts config.irc["frontend"]["nickservPassword"]
        """
        signature = (node, nodes)
        if signature in self._decryptable_nodes:
            return  # Already decrypted
        self._decryptable_nodes.append(signature)
        if self.is_encrypted():
            self._decrypt(node, nodes)

    def schedule(self, minute, hour, month_day, month, week_day):
        """Return a list of tasks scheduled to run at the specified time.

        The schedule data comes from our config file's ``schedule`` field,
        which is stored as :py:attr:`self.data["schedule"] <data>`.
        """
        # Tasks to run this turn, each as a list of either [task_name, kwargs],
        # or just the task_name:
        tasks = []

        now = {"minute": minute, "hour": hour, "month_day": month_day,
                "month": month, "week_day": week_day}

        data = self._data.get("schedule", [])
        for event in data:
            do = True
            for key, value in now.items():
                try:
                    requirement = event[key]
                except KeyError:
                    continue
                if requirement != value:
                    do = False
                    break
            if do:
                try:
                    tasks.extend(event["tasks"])
                except KeyError:
                    pass

        return tasks
