# -*- coding: utf-8  -*-
#
# Copyright (C) 2009-2012 Ben Kurtovic <ben.kurtovic@verizon.net>
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
import re
from textwrap import fill, wrap

try:
    import bcrypt
except ImportError:
    bcrypt = None

try:
    import yaml
except ImportError:
    yaml = None

from earwigbot import exceptions

__all__ = ["ConfigScript"]

class ConfigScript(object):
    """A script to guide a user through the creation of a new config file."""
    WIDTH = 79
    BCRYPT_ROUNDS = 12

    def __init__(self, config):
        self.config = config
        self.data = OrderedDict(
            ("metadata", OrderedDict()),
            ("components", OrderedDict()),
            ("wiki", OrderedDict()),
            ("irc", OrderedDict()),
            ("commands", OrderedDict()),
            ("tasks", OrderedDict()),
            ("schedule", [])
        )

    def _print(self, msg):
        print fill(re.sub("\s\s+", " ", msg), self.WIDTH)

    def _ask(self, text, default=None):
        text = "> " + text
        if default:
            text += " [{0}]".format(default)
        lines = wrap(re.sub("\s\s+", " ", msg), self.WIDTH)
        if len(lines) > 1:
            print "\n".join(lines[:-1])
        return raw_input(lines[-1] + " ") or default

    def _ask_bool(self, text, default=True):
        text = "> " + text
        if default:
            text += " [Y/n]"
        else:
            text += " [y/N]"
        lines = wrap(re.sub("\s\s+", " ", msg), self.WIDTH)
        if len(lines) > 1:
            print "\n".join(lines[:-1])
        while True:
            answer = raw_input(lines[-1] + " ").lower()
            if not answer:
                return default
            if answer.startswith("y"):
                return True
            if answer.startswith("n"):
                return False

    def _set_metadata(self):
        print
        self.data["metadata"] = OrderedDict(("version", 1))
        self._print("""I can encrypt passwords stored in your config file in
                       addition to preventing other users on your system from
                       reading the file. Encryption is recommended is the bot
                       is to run on a public computer like the Toolserver, but
                       otherwise the need to enter a key everytime you start
                       the bot may be annoying.""")
        if self._ask_bool("Encrypt stored passwords?"):
            self.data["metadata"]["encryptPasswords"] = True
            key = getpass("> Enter an encryption key: ")
            print "Running {0} rounds of bcrypt...".format(self.BCRYPT_ROUNDS),
            signature = bcrypt.hashpw(key, bcrypt.gensalt(self.BCRYPT_ROUNDS))
            self.data["metadata"]["signature"] = signature
            print " done."
        else:
            self.data["metadata"]["encryptPasswords"] = False

        self._print("""The bot can temporarily store its logs in the logs/
                       subdirectory. Error logs are kept for a month whereas
                       normal logs are kept for a week. If you disable this,
                       the bot will still print logs to stdout.""")
        question = "Enable logging?"
        self.data["metadata"]["enableLogging"] = self._ask_bool(question)

    def _set_components(self):
        print
        self._print("""The bot contains three separate components that can run
                       independently of each other.""")
        self._print("""- The IRC front-end runs on a normal IRC server, like
                       freenode, and expects users to interact with it through
                       commands.""")
        self._print("""- The IRC watcher runs on a wiki recent-changes server,
                       like irc.wikimedia.org, and listens for edits. Users
                       cannot interact with this component. It can detect
                       specific events and report them to "feed" channels on
                       the front-end, or start bot tasks.""")
        self._print("""- The wiki task scheduler runs wiki-editing bot tasks in
                       separate threads at user-defined times through a
                       cron-like interface. Tasks which are not scheduled can
                       be started by the IRC watcher manually through the IRC
                       front-end.""")
        frontend = self._ask_bool("Enable the IRC front-end?")
        watcher = self._ask_bool("Enable the IRC watcher?")
        scheduler  = self._ask_bool("Enable the wiki task scheduler?")
        self.data["components"]["irc_frontend"] = frontend
        self.data["components"]["irc_watcher"] = watcher
        self.data["components"]["wiki_scheduler"] = scheduler

    def _login(self, kwargs):
        self.config.wiki._load(self.data["wiki"])
        print "Trying to login to the site...",
        try:
            site = self.config.bot.wiki.add_site(**kargs)
        except exceptions.APIError:
            print " API error!"
            question = "Would you like to re-enter the site information?"
            if self._ask_bool(question):
                return self._set_wiki()
            question = "This will cancel the setup process. Are you sure?"
            if self._ask_bool(question, default=False):
                raise exceptions.NoConfigError()
            return self._set_wiki()
        except exceptions.LoginError:
            print " login error!"
            question = "Would you like to re-enter your login information?"
            if self._ask_bool(question):
                self.data["wiki"]["username"] = self._ask("Bot username:")
                self.data["wiki"]["password"] = getpass("> Bot password: ")
                return self._login(kwargs)
            question = "Would you like to re-enter the site information?"
            if self._ask_bool(question):
                return self._set_wiki()
            self._print("""Moving on. You can modify the login information
                           stored in the bot's config in the future.""")
        else:
            print " success."
        return site

    def _set_wiki(self):
        print
        wmf = self._ask_bool("""Will this bot run on Wikimedia Foundation
                                wikis, like Wikipedia?""")
        if wmf:
            msg = "Site project (e.g. 'wikipedia', 'wiktionary', 'wikimedia'):"
            project = self._ask(msg, default="wikipedia").lower()
            msg = "Site language code (e.g. 'en', 'fr', 'commons'):"
            lang = self._ask(msg, default="en").lower()
            kwargs = {"project": project, "lang": lang}
        else:
            msg = "Site base URL, without the script path and trailing slash;"
            msg += " can be protocol-insensitive (e.g. '//en.wikipedia.org'):"
            url = self._ask(msg)
            script = self._ask("Site script path:", default="/w")
            kwargs = {"base_url": url, "script_path": script, "sql": sql}

        self.data["wiki"]["username"] = self._ask("Bot username:")
        self.data["wiki"]["password"] = getpass("> Bot password: ")
        self.data["wiki"]["userAgent"] = "EarwigBot/$1 (Python/$2; https://github.com/earwig/earwigbot)"
        self.data["wiki"]["summary"] = "([[WP:BOT|Bot]]): $2"
        self.data["wiki"]["useHTTPS"] = True
        self.data["wiki"]["assert"] = "user"
        self.data["wiki"]["maxlag"] = 10
        self.data["wiki"]["waitTime"] = 3
        self.data["wiki"]["defaultSite"] = self._login(kwargs).name
        self.data["wiki"]["sql"] = {}

        if wmf:
            msg = "Will this bot run from the Wikimedia Toolserver?"
            toolserver = self._ask_bool(msg, default=False)
            if toolserver:
                args = (("host", "$1-p.rrdb.toolserver.org"), ("db": "$1_p"))
                self.data["wiki"]["sql"] = OrderedDict(args)

        self.data["wiki"]["shutoff"] = {}
        msg = "Would you like to enable an automatic shutoff page for the bot?"
        if self._ask_bool(msg):
            self._print("""The page title can contain two wildcards: $1 will be
                           substituted with the bot's username, and $2 with the
                           current task number. This can be used to implement a
                           separate shutoff page for each task.""")
            page = self._ask("Page title:", default="User:$1/Shutoff")
            disabled = self._ask("Page content when *not* shut off:", "run")
            args = (("page", page), ("disabled", disabled))
            self.data["wiki"]["shutoff"] = OrderedDict(args)

        self.data["wiki"]["search"] = {}

    def _set_irc(self):
        # create permissions.db with us if frontend
        # create rules.py if watcher
        pass

    def _set_commands(self):
        # disable: True if no IRC frontend or prompted
        # create commands/
        pass

    def _set_tasks(self):
        # disable: True if prompted
        # create tasks/
        pass

    def _set_schedule(self):
        pass

    def _save(self):
        with open(self.config.path, "w") as fp:
            yaml.dump(self.data, stream=fp, default_flow_style=False)

    def make_new(self):
        """Make a new config file based on the user's input."""
        self._set_metadata()
        self._set_components()
        self._set_wiki()
        components = self.data["components"]
        if components["irc_frontend"] or components["irc_watcher"]:
            self._set_irc()
            self._set_commands()
        self._set_tasks()
        if components["wiki_scheduler"]:
            self._set_schedule()
        self._print("""I am now saving config.yml with your settings. YAML is a
                       relatively straightforward format and you should be able
                       to update these settings in the future when necessary.
                       I will start the bot at your signal. Feel free to
                       contact me at wikipedia.earwig at gmail.com if you have
                       any questions.""")
        self._save()
        if not self._ask_bool("Start the bot now?"):
            exit()
