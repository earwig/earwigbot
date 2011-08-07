# -*- coding: utf-8  -*-

class BaseCommand(object):
    """A base class for commands on IRC."""

    def __init__(self, connection):
        self.connection = connection

    def get_hooks(self):
        """Hooks are: 'msg', 'msg_private', 'msg_public', and 'join'. Return
        the hooks you want this command to be called on."""
        return []

    def get_help(self, command):
        """Return help information for the command, used by !help. return None
        for no help. If a given class handles multiple commands, the command
        variable can be used to return different help for each one."""
        return None

    def check(self, data):
        """Given a Data() object, return True if we should respond to this
        activity, or False if we should ignore it/it doesn't apply to us. Most
        commands return True if data.command == 'command_name', otherwise
        they return False."""
        return False

    def process(self, data):
        """Handle an activity (usually a message) on IRC. At this point, thanks
        to self.check() which is called automatically by command_handler, we
        know this is something we should respond to, so (usually) a
        'if data.command != "command_name": return' is unnecessary."""
        pass
