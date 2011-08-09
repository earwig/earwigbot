# -*- coding: utf-8  -*-

class BaseCommand(object):
    """A base class for commands on IRC.

    This docstring is reported to the user when they use !help <command>.
    """
    # This is the command's name, as reported to the user when they use !help:
    name = "base_command"
    
    # Hooks are "msg", "msg_private", "msg_public", and "join". "msg" is the
    # default behavior; if you wish to override that, change the value in your
    # command subclass:
    hooks = ["msg"]

    def __init__(self, connection):
        """Constructor for new commands.
        
        This is called once when the command is loaded (from
        commands._load_command()). `connection` is a Connection object,
        allowing us to do self.connection.say(), self.connection.send(), etc,
        from within a method.
        """
        self.connection = connection

    def check(self, data):
        """Returns whether this command should be called in response to 'data'.

        Given a Data() instance, return True if we should respond to this
        activity, or False if we should ignore it or it doesn't apply to us.

        Most commands return True if data.command == self.name, otherwise they
        return False. This is the default behavior of check(); you need only
        override it if you wish to change that.
        """
        if data.is_command and data.command == self.name:
            return True
        return False

    def process(self, data):
        """Main entry point for doing a command.

        Handle an activity (usually a message) on IRC. At this point, thanks
        to self.check() which is called automatically by the command handler,
        we know this is something we should respond to, so (usually) something
        like 'if data.command != "command_name": return' is unnecessary.
        """
        pass
