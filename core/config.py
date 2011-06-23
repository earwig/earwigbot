# -*- coding: utf-8  -*-

"""
EarwigBot's XML Config File Parser

This handles all tasks involving reading and writing to our config file,
including encrypting and decrypting passwords and making a new config file from
scratch at the inital bot run.

Usually you'll just want to do "from core import config" and access config data
from within config's four global variables:

* config.components
* config.wiki
* config.irc
* config.schedule
"""

from collections import defaultdict
from os import makedirs, path
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from lib import blowfish

script_dir = path.dirname(path.abspath(__file__))
root_dir = path.split(script_dir)[0]
config_path = path.join(root_dir, "config.xml")

_config = None  # holds the parsed DOM object for our config file

# initialize our five global variables to store config data
components, wiki, irc, schedule, watcher = (None, None, None, None, None)

class ConfigParseError(Exception):
    """Base exception for when we could not parse the config file."""

class TypeMismatchError(ConfigParseError):
    """A field does not fit to its expected type; e.g., an arbitrary string
    where we expected a boolean or integer."""

class MissingElementError(ConfigParseError):
    """An element in the config file is missing a required sub-element."""

class MissingAttributeError(ConfigParseError):
    """An element is missing a required attribute to be parsed correctly."""

class Container(object):
    """A class to hold information in a nice, accessable manner."""

def _load_config():
    """Load data from our XML config file (config.xml) into a DOM object."""
    global _config
    _config = minidom.parse(config_path)

def verify_config():
    """Check to see if we have a valid config file, and if not, notify the
    user. If there is no config file at all, offer to make one; otherwise,
    exit."""
    if path.exists(config_path):
        try:
            _load_config()
        except ExpatError as error:
            print "Could not parse config file {0}:\n{1}".format(config_path,
                    error)
            exit()
        else:
            if not _config.getElementsByTagName("config"):
                e = "Config file is missing a <config> tag."
                raise MissingElementError(e)
            return are_passwords_encrypted()
    else:
        print "You haven't configured the bot yet!"
        choice = raw_input("Would you like to do this now? [y/n] ")
        if choice.lower().startswith("y"):
            return make_new_config()
        else:
            exit()

def make_new_config():
    """Make a new XML config file based on the user's input."""
    makedirs(config_dir)
    
    encrypt = raw_input("Would you like to encrypt passwords stored in " +
            "config.xml? [y/n] ")
    if encrypt.lower().startswith("y"):
        is_encrypted = True
    else:
        is_encrypted = False
        
    return is_encrypted

def are_passwords_encrypted():
    """Determine if the passwords in our config file are encrypted; return
    either True or False, or raise an exception if there was a problem reading
    the config file."""
    element = _config.getElementsByTagName("config")[0]
    attribute = element.getAttribute("encrypt-passwords")
    if not attribute:
        return False
    return attribute_to_bool(attribute, element, "encrypt-passwords")

def get_first_element(parent, tag_name):
    """Return the first child of the parent element with the given tag name, or
    return None if no child of that name exists."""
    try:
        return parent.getElementsByTagName(tag_name)[0]
    except IndexError:
        return None

def get_required_element(parent, tag_name):
    """Return the first child of the parent element with the given tag name, or
    raise MissingElementError() if no child of that name exists."""
    element = get_first_element(parent, tag_name)
    if not element:
        e = "A <{0}> tag is missing a required <{1}> child tag.".format(
                parent.tagName, tag_name)
        raise MissingElementError(e)
    return element

def get_required_attribute(element, attr_name):
    """Return the value of the attribute 'attr_name' in 'element'. If
    undefined, raise MissingAttributeError()."""
    attribute = element.getAttribute(attr_name)
    if not attribute:
        e = "A <{0}> tag is missing the required attribute '{1}'.".format(
                element.tagName, attr_name)
        raise MissingAttributeError(e)
    return attribute

def attribute_to_bool(value, element, attr_name):
    """Return True if 'value' is 'true', '1', or 'on', return False if it is
    'false', '0', or 'off' (regardless of capitalization), or raise
    TypeMismatchError() if it does match any of those. 'element' and
    'attr_name' are only used to generate the error message."""
    lcase = value.lower()
    if lcase in ["true", "1", "on"]:
        return True
    elif lcase in ["false", "0", "off"]:
        return False
    else:
        e = ("Expected a bool in attribute '{0}' of tag '{1}', but got '{2}'."
                ).format(attr_name, element.tagName, value)
        raise TypeMismatchError(e)

def attribute_to_int(value, element, attr_name):
    """Return 'value' after it is converted to an integer. If it could not be
    converted, raise TypeMismatchError() using 'element' and 'attr_name' only
    to give the user information about what happened."""
    try:
        return int(value)
    except ValueError:
        e = ("Expected an integer in attribute '{0}' of tag '{1}', but got " +
                "'{2}'.").format(attr_name, element.tagName, value)
        raise TypeMismatchError(e)

def parse_config(key):
    """A thin wrapper for the actual config parser in _parse_config(): catch
    parsing exceptions and report them to the user cleanly."""
    try:
        _parse_config(key)
    except ConfigParseError as error:
        print "\nError parsing config file:"
        print error
        exit(1)
    except blowfish.BlowfishError as error:
        print "\nError decrypting passwords:"
        print "{0}: {1}.".format(error.__class__.__name__, error)
        exit(1)

def _parse_config(key):
    """Parse config data from a DOM object into the four global variables that
    store our config info. The key is used to unencrypt passwords stored in the
    XML config file."""
    global components, wiki, irc, schedule

    _load_config()  # we might be re-loading unnecessarily here, but no harm in
                    # that!
    data = _config.getElementsByTagName("config")[0]

    components = parse_components(data)
    wiki = parse_wiki(data, key)
    irc = parse_irc(data, key)
    schedule = parse_schedule(data)

def parse_components(data):
    """Parse everything within the <components> XML tag of our config file.
    The components object here will exist as config.components, and is a dict
    of our enabled components: components[name] = True if it is enabled, False
    if it is disabled."""
    components = defaultdict(lambda: False)  # all components are disabled by
                                             # default
    element = get_required_element(data, "components")

    for component in element.getElementsByTagName("component"):
        name = get_required_attribute(component, "name")
        components[name] = True

    return components

def parse_wiki(data, key):
    """Parse everything within the <wiki> tag of our XML config file."""
    pass

def parse_irc_server(data, key):
    """Parse everything within a <server> tag."""
    server = Container()
    connection = get_required_element(data, "connection")

    server.host = get_required_attribute(connection, "host")
    server.port = get_required_attribute(connection, "port")
    server.nick = get_required_attribute(connection, "nick")
    server.ident = get_required_attribute(connection, "ident")
    server.realname = get_required_attribute(connection, "realname")

    # convert the port from a string to an int
    server.port = attribute_to_int(server.port, connection, "port")

    nickserv = get_first_element(data, "nickserv")
    if nickserv:
        server.nickserv = Container()
        server.nickserv.username = get_required_attribute(nickserv, "username")
        password = get_required_attribute(nickserv, "password")
        if are_passwords_encrypted():
            server.nickserv.password = blowfish.decrypt(key, password)
        else:
            server.nickserv.password = password
    else:
        server.nickserv = None

    server.channels = list()
    channels = get_first_element(data, "channels")
    if channels:
        for channel in channels.getElementsByTagName("channel"):
            name = get_required_attribute(channel, "name")
            server.channels.append(name)

    return server

def parse_irc(data, key):
    """Parse everything within the <irc> tag of our XML config file."""
    irc = Container()

    element = get_first_element(data, "irc")
    if not element:
        return irc

    servers = get_first_element(element, "servers")
    if servers:
        for server in servers.getElementsByTagName("server"):
            server_name = get_required_attribute(server, "name")
            if server_name == "frontend":
                irc.frontend = parse_irc_server(server, key)
            elif server_name == "watcher":
                irc.watcher = parse_irc_server(server, key)
            else:
                print ("Warning: config file specifies a <server> with " +
                "unknown name '{0}'. Ignoring.").format(server_name)

    permissions = get_first_element(element, "permissions")
    if permissions:
        irc.permissions = dict()
        for group in permissions.getElementsByTagName("group"):
            group_name = get_required_attribute(group, "name")
            irc.permissions[group_name] = list()
            for user in group.getElementsByTagName("user"):
                hostname = get_required_attribute(user, "host")
                irc.permissions[group_name].append(hostname)

    return irc  

def parse_schedule(data):
    """Store the <schedule> element in schedule.data and the _schedule()
    function as schedule.check()."""
    schedule = Container()
    schedule.check = _schedule
    schedule.data = get_first_element(data, "schedule")
    return schedule
    
def _schedule(minute, hour, month_day, month, week_day):
    """Return a list of tasks that are scheduled to run at the time specified
    by the function args. The schedule data comes from our config file's
    <schedule> tag, which is stored as schedule.data. Call this function with
    config.schedule.check(args)."""
    tasks = []  # tasks to run this turn, each as a tuple of (task_name,
    # kwargs), or just task_name

    now = {"minute": minute, "hour": hour, "month_day": month_day,
            "month": month, "week_day": week_day}

    for when in schedule.data.getElementsByTagName("when"):
        do = True
        for key, value in now.items():
            if when.hasAttribute(key):
                req = when.getAttribute(key)
                if attribute_to_int(req, when, key) != value:
                    do = False
                    break
        if do:
            for task in when.getElementsByTagName("task"):
                name = get_required_attribute(task, "name")
                args = dict()
                for key in task.attributes.keys():
                    args[key] = task.getAttribute(key)
                del args["name"]
                if args:
                    tasks.append((name, args))
                else:
                    tasks.append(name)

    return tasks
