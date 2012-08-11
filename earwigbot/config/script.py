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
from os import chmod, mkdir, path
import re
import stat
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
from earwigbot.config.ordered_yaml import OrderedDumper

__all__ = ["ConfigScript"]

RULES_TEMPLATE = """"# -*- coding: utf-8  -*-

def process(bot, rc):
    \"\"\"Given a Bot() object and an RC() object, return a list of channels
    to report this event to. Also, start any wiki bot tasks within this
    function if necessary.\"\"\"
    pass
"""

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

        self.wmf = False
        self.proj = None
        self.lang = None

    def _print(self, text):
        print fill(re.sub("\s\s+", " ", text), self.WIDTH)

    def _pause(self):
        raw_input("> Press enter to continue: ")

    def _ask(self, text, default=None):
        text = "> " + text
        if default:
            text += " [{0}]".format(default)
        lines = wrap(re.sub("\s\s+", " ", text), self.WIDTH)
        if len(lines) > 1:
            print "\n".join(lines[:-1])
        return raw_input(lines[-1] + " ") or default

    def _ask_bool(self, text, default=True):
        text = "> " + text
        if default:
            text += " [Y/n]"
        else:
            text += " [y/N]"
        lines = wrap(re.sub("\s\s+", " ", text), self.WIDTH)
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

    def _ask_list(self, text):
        print fill(re.sub("\s\s+", " ", "> " + text), self.WIDTH)
        print "[one item per line; blank line to end]:"
        result = []
        while True:
            line = raw_input("> ")
            if line:
                result.append(line)
            else:
                return result

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
        logging = self._ask_bool("Enable logging?")
        self.data["metadata"]["enableLogging"] = logging

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
            site = self.config.bot.wiki.add_site(**kwargs)
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
        self.wmf = self._ask_bool("""Will this bot run on Wikimedia Foundation
                                     wikis, like Wikipedia?""")
        if self.wmf:
            msg = "Site project (e.g. 'wikipedia', 'wiktionary', 'wikimedia'):"
            self.proj = project = self._ask(msg, default="wikipedia").lower()
            msg = "Site language code (e.g. 'en', 'fr', 'commons'):"
            self.lang = lang = self._ask(msg, default="en").lower()
            kwargs = {"project": project, "lang": lang}
        else:
            msg = "Site base URL, without the script path and trailing slash;"
            msg += " can be protocol-insensitive (e.g. '//en.wikipedia.org'):"
            url = self._ask(msg)
            script = self._ask("Site script path:", default="/w")
            kwargs = {"base_url": url, "script_path": script}

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

        if self.wmf:
            msg = "Will this bot run from the Wikimedia Toolserver?"
            toolserver = self._ask_bool(msg, default=False)
            if toolserver:
                args = (("host", "$1-p.rrdb.toolserver.org"), ("db", "$1_p"))
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
        if self.data["components"]["irc_frontend"]:
            print
            frontend = self.data["irc"]["frontend"] = OrderedDict()
            msg = "Hostname of the frontend's IRC server, without 'irc://':"
            frontend["host"] = self._ask(msg, "irc.freenode.net")
            frontend["port"] = self._ask("Frontend port:", 6667)
            frontend["nick"] = self._ask("Frontend bot's nickname:")
            frontend["ident"] = self._ask("Frontend bot's ident:",
                                          frontend["nick"].lower())
            question = "Frontend bot's real name (gecos):"
            frontend["realname"] = self._ask(question)
            if self._ask_bool("Should the bot identify to NickServ?"):
                frontend["nickservUsername"] = self._ask("NickServ username:",
                                                         frontend["nick"])
                frontend["nickservPassword"] = getpass("> Nickserv password: ")
            chan_question = "Frontend channels to join by default:"
            frontend["channels"] = self._ask_list(chan_question)
            self._print("""The bot keeps a database of its admins (users who
                           can use certain sensitive commands) and owners
                           (users who can quit the bot and modify its access
                           list), identified by nick, ident, and/or hostname.
                           Hostname is most secure since it cannot be easily
                           spoofed. If you have a cloak, it will probably look
                           like 'wikipedia/Username' or
                           'unaffiliated/nickname'.""")
            host = self._ask("Your hostname on the IRC frontend:")
            if host:
                permdb = self.config._permissions
                permdb.load()
                permdb.add_owner(host=host)
                permdb.add_admin(host=host)
        else:
            frontend = {}

        if self.data["components"]["irc_watcher"]:
            print
            watcher = self.data["irc"]["watcher"] = OrderedDict()
            if self.wmf:
                watcher["host"] = "irc.wikimedia.org"
                watcher["port"] = 6667
            else:
                msg = "Hostname of the watcher's IRC server, without 'irc://':"
                watcher["host"] = self._ask(msg)
                watcher["port"] = self._ask("Watcher port:", 6667)
            watcher["nick"] = self._ask("Watcher bot's nickname:",
                                        frontend.get("nick"))
            watcher["ident"] = self._ask("Watcher bot's ident:",
                                         watcher["nick"].lower())
            question = "Watcher bot's real name (gecos):"
            watcher["realname"] = self._ask(question, frontend.get("realname"))
            watcher_ns = "Should the bot identify to NickServ?"
            if not self.wmf and self._ask_bool(watcher_ns):
                watcher["nickservUsername"] = self._ask("NickServ username:",
                                                        watcher["nick"])
                watcher["nickservPassword"] = getpass("> Nickserv password: ")
            if self.wmf:
                watcher["channels"] = ["#{0}.{1}".format(self.lang, self.proj)]
            else:
                chan_question = "Watcher channels to join by default:"
                watcher["channels"] = self._ask_list(chan_question)
            self._print("""I am now creating a blank 'rules.py' file, which
                           will determine how the bot handles messages received
                           from the IRC watcher. It contains a process()
                           function that takes a Bot object allowing you to
                           start tasks and an RC object that holds the message
                           from the watcher. See the documentation for
                           details.""")
            with open(path.join(self.config.root_dir, "rules.py"), "w") as fp:
                fp.write(RULES_TEMPLATE)
            self._pause()

        self.data["irc"]["version"] = "EarwigBot - $1 - Python/$2 https://github.com/earwig/earwigbot"

    def _set_commands(self):
        print
        msg = """Would you like to disable the default IRC commands? You can
                 fine-tune which commands are disabled later on."""
        if (not self.data["components"]["irc_frontend"] or
                self._ask_bool(msg, default=False)):
            self.data["commands"]["disable"] = True
        self._print("""I am now creating the 'commands/' directory, where you
                       can place custom IRC commands and plugins. Creating your
                       own commands is described in the documentation.""")
        mkdir(path.join(self.config.root_dir, "commands"))
        self._pause()

    def _set_tasks(self):
        print
        self._print("""I am now creating the 'tasks/' directory, where you can
                       place custom bot tasks and plugins. Creating your own
                       tasks is described in the documentation.""")
        mkdir(path.join(self.config.root_dir, "tasks"))
        self._pause()

    def _set_schedule(self):
        self._print("""The final section of your config file, 'schedule', is a
                       list of bot tasks to be started by the wiki scheduler.
                       Each entry contains cron-like time quantifiers and a
                       list of tasks. For example, the following starts the
                       'foobot' task every hour on the half-hour:""")
        print "schedule:"
        print "    - minute: 30"
        print "      tasks:"
        print "          - foobot"
        self._print("""The following starts the 'barbot' task with the keyword
                       arguments 'action="baz"' every Monday at 05:00 UTC:""")
        print "    - week_day: 1"
        print "      hour:     5"
        print "      tasks:"
        print '          - ["barbot", {"action": "baz"}]'
        self._print("""The full list of quantifiers is minute, hour, month_day,
                       month, and week_day. See the documentation for more
                       details.""")
        self._pause()

    def _save(self):
        with open(self.config.path, "w") as strm:
            yaml.dump(self.data, strm, OrderedDumper, default_flow_style=False)

    def make_new(self):
        """Make a new config file based on the user's input."""
        try:
            open(self.config.path, "w").close()
            chmod(self.config.path, stat.S_IRUSR|stat.S_IWUSR)
        except IOError:
            print "I can't seem to write to the config file:"
            raise
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
                       contact me at wikipedia.earwig@gmail.com if you have any
                       questions.""")
        self._save()
        if not self._ask_bool("Start the bot now?"):
            exit()
