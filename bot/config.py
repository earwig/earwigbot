# -*- coding: utf-8  -*-

"""
EarwigBot's JSON Config File Parser

This handles all tasks involving reading and writing to our config file,
including encrypting and decrypting passwords and making a new config file from
scratch at the inital bot run.

Usually you'll just want to do "from core import config" and access config data
from within config's three global variables and one function:

* config.components       - a list of enabled components
* config.wiki             - a dict of config information for wiki-editing
* config.irc              - a dict of config information for IRC
* config.schedule()       - returns a list of tasks scheduled to run at a given
                            time
"""

import json
from os import path

import blowfish

script_dir = path.dirname(path.abspath(__file__))
root_dir = path.split(script_dir)[0]
config_path = path.join(root_dir, "config.json")

_config = None  # holds data loaded from our config file

# set our three easy-config-access global variables to None
components, wiki, irc = (None, None, None)

def is_config_loaded():
    """Return True if our config file has already been loaded, and False if it
    hasn't."""
    if _config is not None:
        return True
    return False

def load_config():
    """Load data from our JSON config file (config.json) into _config."""
    global _config
    with open(config_path, 'r') as fp:
        try:
            _config = json.load(fp)
        except ValueError as error:
            print "Error parsing config file {0}:".format(config_path)
            print error
            exit(1)

def verify_config():
    """Check to see if we have a valid config file, and if not, notify the
    user. If there is no config file at all, offer to make one; otherwise,
    exit. If everything goes well, return True if stored passwords are
    encrypted in the file, or False if they are not."""
    if path.exists(config_path):
        load_config()
        try:
            return _config["encryptPasswords"]  # are passwords encrypted?
        except KeyError:
            return False  # assume passwords are not encrypted by default
    else:
        print "You haven't configured the bot yet!"
        choice = raw_input("Would you like to do this now? [y/n] ")
        if choice.lower().startswith("y"):
            return make_new_config()
        else:
            exit(1)

def parse_config(key):
    """Store data from our config file in three global variables for easy
    access, and use the key to unencrypt passwords. Catch password decryption
    errors and report them to the user."""
    global components, wiki, irc

    load_config()  # we might be re-loading unnecessarily here, but no harm in
                   # that!
    try:
        components = _config["components"]
    except KeyError:
        components = []
    try:
        wiki = _config["wiki"]
    except KeyError:
        wiki = {}
    try:
        irc = _config["irc"]
    except KeyError:
        irc = {}

    try:
        try:
            if _config["encryptPasswords"]:
                decrypt(key, "wiki['password']")
                decrypt(key, "irc['frontend']['nickservPassword']")
                decrypt(key, "irc['watcher']['nickservPassword']")
        except KeyError:
            pass
    except blowfish.BlowfishError as error:
        print "\nError decrypting passwords:"
        print "{0}: {1}.".format(error.__class__.__name__, error)
        exit(1)

def decrypt(key, item):
    """Decrypt 'item' with blowfish.decrypt() using the given key and set it to
    the decrypted result. 'item' should be a string, like
    decrypt(key, "wiki['password']"), NOT decrypt(key, wiki['password'),
    because that won't work."""
    global irc, wiki
    try:
        result = blowfish.decrypt(key, eval(item))
    except KeyError:
        return
    exec "{0} = result".format(item)

def schedule(minute, hour, month_day, month, week_day):
    """Return a list of tasks that are scheduled to run at the time specified
    by the function arguments. The schedule data comes from our config file's
    'schedule' field, which is stored as _config["schedule"]. Call this
    function with config.schedule(args)."""
    tasks = []  # tasks to run this turn, each as a tuple of either (task_name,
    # kwargs), or just task_name

    now = {"minute": minute, "hour": hour, "month_day": month_day,
            "month": month, "week_day": week_day}

    try:
        data = _config["schedule"]
    except KeyError:
        return []  # nothing is in our schedule
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

def make_new_config():
    """Make a new config file based on the user's input."""

    encrypt = raw_input("Would you like to encrypt passwords stored in " +
            "config.json? [y/n] ")
    if encrypt.lower().startswith("y"):
        is_encrypted = True
    else:
        is_encrypted = False

    return is_encrypted
