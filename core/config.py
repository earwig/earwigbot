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

def parse_config(key):
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
    element = data.getElementsByTagName("components")
    if not element:
        e = "<config> is missing a required <components> tag."
        raise MissingElementException(e)
    element = element[0]  # select the first <components> tag out of our list
                          # of tags, even though we should only have one

    component_tags = element.getElementsByTagName("component")
    for component in component_tags:
        name = component.getAttribute("name")
        if not name:
            e = "A <component> tag is missing the required attribute 'name'."
            raise MissingAttributeException(e)
        is_enabled = attribute_to_bool(component, "enabled", False)
        components[name] = is_enabled

    return components

def parse_wiki(data, key):
    pass
    
def parse_irc(data, key):
    pass
    
def parse_schedule(data):
    pass
    
def parse_watcher(data):
    pass
