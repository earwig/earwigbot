# -*- coding: utf-8  -*-

"""
EarwigBot's XML Config File Parser

This handles all tasks involving reading and writing to our config file,
including encrypting and decrypting passwords and making a new config file from
scratch at the inital bot run.

Usually you'll just want to do "from core.config import config" and access
config data from within that object.
"""

from collections import defaultdict
from os import makedirs, path
from xml.dom import minidom
from xml.parsers.expat import ExpatError

script_dir = path.dirname(path.abspath(__file__))
root_dir = path.split(script_dir)[0]
config_path = path.join(root_dir, "config.xml")

_config = None  # holds the parsed DOM object for our config file
config = None  # holds an instance of Container() with our config data

class ConfigParseException(Exception):
    """Base exception for when we could not parse the config file."""

class TypeMismatchException(ConfigParseException):
    """A field does not fit to its expected type; e.g., an arbitrary string
    where we expected a boolean or integer."""

class MissingElementException(ConfigParseException):
    """An element in the config file is missing a required sub-element."""

class MissingAttributeException(ConfigParseException):
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
                raise MissingElementException(e)
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

def encrypt_password(password, key):
    """If passwords are supposed to be encrypted, use this function to do that
    using a user-provided key."""
    # TODO: stub
    return password

def decrypt_password(password, key):
    """If passwords are encrypted, use this function to decrypt them using a
    user-provided key."""
    # TODO: stub
    return password

def are_passwords_encrypted():
    """Determine if the passwords in our config file are encrypted, returning
    either True or False."""
    element = _config.getElementsByTagName("config")[0]
    return attribute_to_bool(element, "encrypt-passwords", default=False)

def attribute_to_bool(element, attribute, default=None):
    """Return True if the value of element's attribute is 'true', '1', or 'on';
    return False if it is 'false', '0', or 'off' (regardless of
    capitalization); return default if it is empty; raise TypeMismatchException
    if it does match any of those."""
    value = element.getAttribute(attribute).lower()
    if value in ["true", "1", "on"]:
        return True
    elif value in ["false", "0", "off"]:
        return False
    elif value == '':
        return default
    else:
        e = ("Expected a bool in attribute '{0}' of element '{1}', but " +
        "got '{2}'.").format(attribute, element.tagName, value)
        raise TypeMismatchException(e)

def get_first_element(parent, tag_name):
    """Return the first child of the parent element with the given tag name, or
    return None if no child of that name exists."""
    try:
        return parent.getElementsByTagName(tag_name)[0]
    except IndexError:
        return None

def get_required_element(parent, tag_name):
    """Return the first child of the parent element with the given tag name, or
    raise MissingElementException() if no child of that name exists."""
    element = get_first_element(parent, tag_name)
    if not element:
        e = "A <{0}> tag is missing a required <{1}> child tag.".format(
                parent.tagName, tag_name)
        raise MissingElementException(e)
    return element

def get_required_attribute(element, attr_name):
    """Return the value of the attribute 'attr_name' in 'element'. If
    undefined, raise MissingAttributeException()."""
    attribute = element.getAttribute(attr_name)
    if not attribute:
        e = "A <{0}> tag is missing the required attribute '{1}'.".format(
                element.tagName, attr_name)
        raise MissingAttributeException(e)
    return attribute

def parse_config(key):
    """A thin wrapper for the actual config parser in _parse_config(): catch
    parsing exceptions and report them to the user cleanly."""
    try:
        _parse_config(key)
    except ConfigParseException as e:
        print "\nError parsing config file:"
        print e
        exit(1)

def _parse_config(key):
    """Parse config data from a DOM object into the 'config' global variable.
    The key is used to unencrypt passwords stored in the XML config file."""
    _load_config()  # we might be re-loading unnecessarily here, but no harm in
                    # that!
    data = _config.getElementsByTagName("config")[0]

    cfg = Container()
    cfg.components = parse_components(data)
    cfg.wiki = parse_wiki(data, key)
    cfg.irc = parse_irc(data, key)
    cfg.schedule = parse_schedule(data)
    cfg.watcher = parse_watcher(data)

    global config
    config = cfg

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

    nickserv = get_first_element(data, "nickserv")
    if nickserv:
        server.nickserv = Container()
        server.nickserv.username = get_required_attribute(nickserv, "username")
        password = get_required_attribute(nickserv, "password")
        if are_passwords_encrypted():
            server.nickserv.password = decrypt_password(password, key)
        else:
            server.nickserv.password = password

    channels = get_first_element(data, "channels")
    if channels:
        server.channels = list()
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
    """Parse everything within the <schedule> tag of our XML config file."""
    pass
    
def parse_watcher(data):
    """Parse everything within the <watcher> tag of our XML config file."""
    pass
