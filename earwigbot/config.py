# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
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

from getpass import getpass
import logging
import logging.handlers
from os import mkdir, path

import yaml

from earwigbot import blowfish

__all__ = ["BotConfig"]

class BotConfig(object):
    """
    EarwigBot's YAML Config File Manager

    This handles all tasks involving reading and writing to our config file,
    including encrypting and decrypting passwords and making a new config file
    from scratch at the inital bot run.

    BotConfig has a few properties and functions, including the following:
    * config.root_dir    - bot's working directory; contains config.yml, logs/
    * config.path        - path to the bot's config file
    * config.components  - enabled components
    * config.wiki        - information about wiki-editing
    * config.tasks       - information for bot tasks
    * config.irc         - information about IRC
    * config.metadata    - miscellaneous information
    * config.schedule()  - tasks scheduled to run at a given time

    BotConfig also has some functions used in config loading:
    * config.load()     - loads and parses our config file, returning True if
                          passwords are stored encrypted or False otherwise;
                          can also be used to easily reload config
    * config.decrypt()  - given a key, decrypts passwords inside our config
                          variables, and remembers to decrypt the password if
                          config is reloaded; won't do anything if passwords
                          aren't encrypted
    """

    def __init__(self, root_dir):
        self._root_dir = root_dir
        self._config_path = path.join(self._root_dir, "config.yml")
        self._log_dir = path.join(self._root_dir, "logs")
        self._decryption_key = None
        self._data = None

        self._components = _ConfigNode()
        self._wiki = _ConfigNode()
        self._tasks = _ConfigNode()
        self._irc = _ConfigNode()
        self._metadata = _ConfigNode()

        self._nodes = [self._components, self._wiki, self._tasks, self._irc,
                       self._metadata]
        self._decryptable_nodes = []

    def _load(self):
        """Load data from our JSON config file (config.yml) into self._data."""
        filename = self._config_path
        with open(filename, 'r') as fp:
            try:
                self._data = yaml.load(fp)
            except yaml.YAMLError as error:
                print "Error parsing config file {0}:".format(filename)
                raise

    def _setup_logging(self):
        """Configures the logging module so it works the way we want it to."""
        log_dir = self._log_dir
        logger = logging.getLogger("earwigbot")
        logger.setLevel(logging.DEBUG)

        if self.metadata.get("enableLogging"):
            hand = logging.handlers.TimedRotatingFileHandler
            formatter = _BotFormatter()
            color_formatter = _BotFormatter(color=True)

            logfile = lambda f: path.join(log_dir, f)

            if not path.isdir(log_dir):
                if not path.exists(log_dir):
                    mkdir(log_dir, 0700)
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

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(color_formatter)
        logger.addHandler(stream_handler)

    def _decrypt(self, node, nodes):
        """Try to decrypt the contents of a config node. Use self.decrypt()."""
        try:
            node._decrypt(self._decryption_key, nodes[:-1], nodes[-1])
        except blowfish.BlowfishError as error:
            print "Error decrypting passwords:"
            raise

    def _make_new(self):
        """Make a new config file based on the user's input."""
        #m = "Would you like to encrypt passwords stored in config.yml? [y/n] "
        #encrypt = raw_input(m)
        #if encrypt.lower().startswith("y"):
        #    is_encrypted = True
        #else:
        #    is_encrypted = False
        raise NotImplementedError()
        # yaml.dumps()

    @property
    def root_dir(self):
        return self._root_dir

    @property
    def path(self):
        return self._config_path

    @property
    def log_dir(self):
        return self._log_dir

    @property
    def data(self):
        """The entire config file."""
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
    def tasks(self):
        """A dict of information for bot tasks."""
        return self._tasks

    @property
    def irc(self):
        """A dict of information about IRC."""
        return self._irc

    @property
    def metadata(self):
        """A dict of miscellaneous information."""
        return self._metadata

    def is_loaded(self):
        """Return True if our config file has been loaded, otherwise False."""
        return self._data is not None

    def is_encrypted(self):
        """Return True if passwords are encrypted, otherwise False."""
        return self.metadata.get("encryptPasswords", False)

    def load(self):
        """Load, or reload, our config file.

        First, check if we have a valid config file, and if not, notify the
        user. If there is no config file at all, offer to make one, otherwise
        exit.

        Store data from our config file in five _ConfigNodes (components,
        wiki, tasks, irc, metadata) for easy access (as well as the internal
        _data variable).

        If config is being reloaded, encrypted items will be automatically
        decrypted if they were decrypted beforehand.
        """
        if not path.exists(self._config_path):
            print "Config file not found:", self._config_path
            choice = raw_input("Would you like to create a config file now? [y/n] ")
            if choice.lower().startswith("y"):
                self._make_new()
            else:
                exit(1)

        self._load()
        data = self._data
        self.components._load(data.get("components", {}))
        self.wiki._load(data.get("wiki", {}))
        self.tasks._load(data.get("tasks", {}))
        self.irc._load(data.get("irc", {}))
        self.metadata._load(data.get("metadata", {}))

        self._setup_logging()
        if self.is_encrypted():
            if not self._decryption_key:
                key = getpass("Enter key to decrypt bot passwords: ")
                self._decryption_key = key
            for node, nodes in self._decryptable_nodes:
                self._decrypt(node, nodes)

    def decrypt(self, node, *nodes):
        """Use self._decryption_key to decrypt an object in our config tree.

        If this is called when passwords are not encrypted (check with
        config.is_encrypted()), nothing will happen. We'll also keep track of
        this node if config.load() is called again (i.e. to reload) and
        automatically decrypt it.

        Example usage:
        config.decrypt(config.irc, "frontend", "nickservPassword")
        -> decrypts config.irc["frontend"]["nickservPassword"]
        """
        self._decryptable_nodes.append((node, nodes))
        if self.is_encrypted():
            self._decrypt(node, nodes)

    def schedule(self, minute, hour, month_day, month, week_day):
        """Return a list of tasks scheduled to run at the specified time.

        The schedule data comes from our config file's 'schedule' field, which
        is stored as self._data["schedule"]. Call this function as
        config.schedule(args).
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


class _ConfigNode(object):
    def __iter__(self):
        for key in self.__dict__.iterkeys():
            yield key

    def __getitem__(self, item):
        return self.__dict__.__getitem__(item)

    def _dump(self):
        data = self.__dict__.copy()
        for key, val in data.iteritems():
            if isinstance(val, _ConfigNode):
                data[key] = val._dump()
        return data

    def _load(self, data):
        self.__dict__ = data.copy()

    def _decrypt(self, key, intermediates, item):
        base = self.__dict__
        try:
            for inter in intermediates:
                base = base[inter]
        except KeyError:
            return
        if item in base:
            base[item] = blowfish.decrypt(key, base[item])

    def get(self, *args, **kwargs):
        return self.__dict__.get(*args, **kwargs)


class _BotFormatter(logging.Formatter):
    def __init__(self, color=False):
        self._format = super(_BotFormatter, self).format
        if color:
            fmt = "[%(asctime)s %(lvl)s] %(name)s: %(message)s"
            self.format = lambda record: self._format(self.format_color(record))
        else:
            fmt = "[%(asctime)s %(levelname)-8s] %(name)s: %(message)s"
            self.format = self._format
        datefmt = "%Y-%m-%d %H:%M:%S"
        super(_BotFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def format_color(self, record):
        l = record.levelname.ljust(8)
        if record.levelno == logging.DEBUG:
            record.lvl = l.join(("\x1b[34m", "\x1b[0m"))  # Blue
        if record.levelno == logging.INFO:
            record.lvl = l.join(("\x1b[32m", "\x1b[0m"))  # Green
        if record.levelno == logging.WARNING:
            record.lvl = l.join(("\x1b[33m", "\x1b[0m"))  # Yellow
        if record.levelno == logging.ERROR:
            record.lvl = l.join(("\x1b[31m", "\x1b[0m"))  # Red
        if record.levelno == logging.CRITICAL:
            record.lvl = l.join(("\x1b[1m\x1b[31m", "\x1b[0m"))  # Bold red
        return record
