# -*- coding: utf-8  -*-

## EarwigBot's Config File Parser

from collections import defaultdict
import ConfigParser as configparser
import os

main_cfg_path = os.path.join("config", "main.cfg")
secure_cfg_path = os.path.join("config", "secure.cfg")

config = dict()

def load_config_file(filename):
    parser = configparser.SafeConfigParser()
    parser.optionxform = str # don't lowercase option names automatically
    parser.read(filename)
    return parser

def make_new_config():
    print "You haven't configured the bot yet!"
    choice = raw_input("Would you like to do this now? [y/n] ")
    if choice.lower().startswith("y"):
        pass
    else:
        exit()

def dump_config_to_dict(parsers):
    global config
    for parser in parsers:
        for section in parser.sections():
            for option in parser.options(section):
                try:
                    config[section][option] = parser.get(section, option)
                except KeyError:
                    config[section] = defaultdict(lambda: None)
                    config[section][option] = parser.get(section, option)

def load():
    if not os.path.exists(main_cfg_path):
        make_new_config()
    
    main_cfg = load_config_file(main_cfg_path)
    secure_cfg = load_config_file(secure_cfg_path)
    
    dump_config_to_dict([main_cfg, secure_cfg])
