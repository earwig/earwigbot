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

"""
EarwigBot's Wiki Toolset: Misc Functions

This module, a component of the wiki package, contains miscellaneous functions
that are not methods of any class, like get_site().

There's no need to import this module explicitly. All functions here are
automatically available from earwigbot.wiki.
"""

from cookielib import LWPCookieJar, LoadError
import errno
from getpass import getpass
from os import chmod, path
import platform
import stat

import earwigbot
from earwigbot.config import config
from earwigbot.wiki.exceptions import SiteNotFoundError
from earwigbot.wiki.site import Site

__all__ = ["get_site", "add_site", "del_site"]

_cookiejar = None

def _load_config():
    """Called by a config-requiring function, such as get_site(), when config
    has not been loaded. This will usually happen only if we're running code
    directly from Python's interpreter and not the bot itself, because
    earwigbot.py or core/main.py will already call these functions.
    """
    is_encrypted = config.load()
    if is_encrypted:  # Passwords in the config file are encrypted
        key = getpass("Enter key to unencrypt bot passwords: ")
        config._decryption_key = key
        config.decrypt(config.wiki, "password")

def _get_cookiejar():
    """Returns a LWPCookieJar object loaded from our .cookies file. The same
    one is returned every time.

    The .cookies file is located in the project root, same directory as
    config.json and earwigbot.py. If it doesn't exist, we will create the file
    and set it to be readable and writeable only by us. If it exists but the
    information inside is bogus, we will ignore it.

    This is normally called by _get_site_object_from_dict() (in turn called by
    get_site()), and the cookiejar is passed to our Site's constructor, used
    when it makes API queries. This way, we can easily preserve cookies between
    sites (e.g., for CentralAuth), making logins easier.
    """
    global _cookiejar
    if _cookiejar is not None:
        return _cookiejar

    cookie_file = path.join(config.root_dir, ".cookies")
    _cookiejar = LWPCookieJar(cookie_file)

    try:
        _cookiejar.load()
    except LoadError:
        pass  # File contains bad data, so ignore it completely
    except IOError as e:
        if e.errno == errno.ENOENT:  # "No such file or directory"
            # Create the file and restrict reading/writing only to the owner,
            # so others can't peak at our cookies:
            open(cookie_file, "w").close()
            chmod(cookie_file, stat.S_IRUSR|stat.S_IWUSR)
        else:
            raise

    return _cookiejar

def _get_site_object_from_dict(name, d):
    """Return a Site object based on the contents of a dict, probably acquired
    through our config file, and a separate name.
    """
    project = d.get("project")
    lang = d.get("lang")
    base_url = d.get("baseURL")
    article_path = d.get("articlePath")
    script_path = d.get("scriptPath")
    sql = d.get("sql", {})
    namespaces = d.get("namespaces", {})
    login = (config.wiki.get("username"), config.wiki.get("password"))
    cookiejar = _get_cookiejar()
    user_agent = config.wiki.get("userAgent")
    assert_edit = config.wiki.get("assert")
    maxlag = config.wiki.get("maxlag")

    if user_agent:
        user_agent = user_agent.replace("$1", earwigbot.__version__)
        user_agent = user_agent.replace("$2", platform.python_version())

    for key, value in namespaces.items():  # Convert string keys to integers
        del namespaces[key]
        try:
            namespaces[int(key)] = value
        except ValueError:  # Data is broken, ignore it
            namespaces = None
            break

    return Site(name=name, project=project, lang=lang, base_url=base_url,
                article_path=article_path, script_path=script_path, sql=sql,
                namespaces=namespaces, login=login, cookiejar=cookiejar,
                user_agent=user_agent, assert_edit=assert_edit, maxlag=maxlag)

def get_site(name=None, project=None, lang=None):
    """Returns a Site instance based on information from our config file.

    With no arguments, returns the default site as specified by our config
    file. This is default = config.wiki["defaultSite"];
    config.wiki["sites"][default].

    With `name` specified, returns the site specified by
    config.wiki["sites"][name].

    With `project` and `lang` specified, returns the site specified by the
    member of config.wiki["sites"], `s`, for which s["project"] == project and
    s["lang"] == lang.

    We will attempt to login to the site automatically
    using config.wiki["username"] and config.wiki["password"] if both are
    defined.

    Specifying a project without a lang or a lang without a project will raise
    TypeError. If all three args are specified, `name` will be first tried,
    then `project` and `lang`. If, with any number of args, a site cannot be
    found in the config, SiteNotFoundError is raised.
    """
    # Check if config has been loaded, and load it if it hasn't:
    if not config.is_loaded():
        _load_config()

    # Someone specified a project without a lang (or a lang without a project)!
    if (project is None and lang is not None) or (project is not None and
                                                  lang is None):
        e = "Keyword arguments 'lang' and 'project' must be specified together."
        raise TypeError(e)

    # No args given, so return our default site (project is None implies lang
    # is None, so we don't need to add that in):
    if name is None and project is None:
        try:
            default = config.wiki["defaultSite"]
        except KeyError:
            e = "Default site is not specified in config."
            raise SiteNotFoundError(e)
        try:
            site = config.wiki["sites"][default]
        except KeyError:
            e = "Default site specified by config is not in the config's sites list."
            raise SiteNotFoundError(e)
        return _get_site_object_from_dict(default, site)

    # Name arg given, but don't look at others unless `name` isn't found:
    if name is not None:
        try:
            site = config.wiki["sites"][name]
        except KeyError:
            if project is None:  # Implies lang is None, so only name was given
                e = "Site '{0}' not found in config.".format(name)
                raise SiteNotFoundError(e)
            for sitename, site in config.wiki["sites"].items():
                if site["project"] == project and site["lang"] == lang:
                    return _get_site_object_from_dict(sitename, site)
            e = "Neither site '{0}' nor site '{1}:{2}' found in config."
            e.format(name, project, lang)
            raise SiteNotFoundError(e)
        else:
            return _get_site_object_from_dict(name, site)

    # If we end up here, then project and lang are both not None:
    for sitename, site in config.wiki["sites"].items():
        if site["project"] == project and site["lang"] == lang:
            return _get_site_object_from_dict(sitename, site)
    e = "Site '{0}:{1}' not found in config.".format(project, lang)
    raise SiteNotFoundError(e)

def add_site():
    """STUB: config editing is required first.

    Returns True if the site was added successfully or False if the site was
    already in our config. Raises ConfigError if saving the updated file failed
    for some reason."""
    pass

def del_site(name):
    """STUB: config editing is required first.

    Returns True if the site was removed successfully or False if the site was
    not in our config originally. Raises ConfigError if saving the updated file
    failed for some reason."""
    pass
