# coding=utf-8
"""This contains decorators and tools for creating callable plugin functions.
"""
# Copyright 2013, Ari Koivula, <ari@koivu.la>
# Copyright © 2013, Elad Alfassa <elad@fedoraproject.org>
# Copyright 2013, Lior Ramati <firerogue517@gmail.com>
# Licensed under the Eiffel Forum License 2.

from __future__ import unicode_literals, absolute_import, print_function, division

import sopel.test_tools
import functools

NOLIMIT = 1
"""Return value for ``callable``\s, which supresses rate limiting for the call.

Returning this value means the triggering user will not be
prevented from triggering the command again within the rate limit. This can
be used, for example, to allow a user to rety a failed command immediately.

.. versionadded:: 4.0
"""

VOICE = 1
HALFOP = 2
OP = 4
ADMIN = 8
OWNER = 16


def unblockable(function):
    """Decorator which exempts the function from nickname and hostname blocking.

    This can be used to ensure events such as JOIN are always recorded.
    """
    function.unblockable = True
    return function


def interval(*args):
    """Decorates a function to be called by the bot every X seconds.

    This decorator can be used multiple times for multiple intervals, or all
    intervals can be given at once as arguments. The first time the function
    will be called is X seconds after the bot was started.

    Unlike other plugin functions, ones decorated by interval must only take a
    :class:`sopel.bot.Sopel` as their argument; they do not get a trigger. The
    bot argument will not have a context, so functions like ``bot.say()`` will
    not have a default destination.

    There is no guarantee that the bot is connected to a server or joined a
    channel when the function is called, so care must be taken.

    Example:::

        import sopel.module
        @sopel.module.interval(5)
        def spam_every_5s(bot):
            if "#here" in bot.channels:
                bot.msg("#here", "It has been five seconds!")

    """
    def add_attribute(function):
        if not hasattr(function, "interval"):
            function.interval = []
        for arg in args:
            function.interval.append(arg)
        return function

    return add_attribute


def rule(value):
    """Decorate a function to be called when a line matches the given pattern

    This decorator can be used multiple times to add more rules.

    Args:
        value: A regular expression which will trigger the function.

    If the Sopel instance is in a channel, or sent a PRIVMSG, where a string
    matching this expression is said, the function will execute. Note that
    captured groups here will be retrievable through the Trigger object later.

    Inside the regular expression, some special directives can be used. $nick
    will be replaced with the nick of the bot and , or :, and $nickname will be
    replaced with the nick of the bot.
    """
    def add_attribute(function):
        if not hasattr(function, "rule"):
            function.rule = []
        function.rule.append(value)
        return function

    return add_attribute


def thread(value):
    """Decorate a function to specify if it should be run in a separate thread.

    Functions run in a separate thread (as is the default) will not prevent the
    bot from executing other functions at the same time. Functions not run in a
    separate thread may be started while other functions are still running, but
    additional functions will not start until it is completed.

    Args:
        value: Either True or False. If True the function is called in
            a separate thread. If False from the main thread.

    """
    def add_attribute(function):
        function.thread = value
        return function
    return add_attribute


def commands(*command_list):
    """Decorate a function to set one or more commands to trigger it.

    This decorator can be used to add multiple commands to one callable in a
    single line. The resulting match object will have the command as the first
    group, rest of the line, excluding leading whitespace, as the second group.
    Parameters 1 through 4, seperated by whitespace, will be groups 3-6.

    Args:
        command: A string, which can be a regular expression.

    Returns:
        A function with a new command appended to the commands
        attribute. If there is no commands attribute, it is added.

    Example:
        @commands("hello"):
            If the command prefix is "\.", this would trigger on lines starting
            with ".hello".

        @commands('j', 'join')
            If the command prefix is "\.", this would trigger on lines starting
            with either ".j" or ".join".

    """
    def add_attribute(function):
        if not hasattr(function, "commands"):
            function.commands = []
        function.commands.extend(command_list)
        return function
    return add_attribute


def nickname_commands(*command_list):
    """Decorate a function to trigger on lines starting with "$nickname: command".

    This decorator can be used multiple times to add multiple rules. The
    resulting match object will have the command as the first group, rest of
    the line, excluding leading whitespace, as the second group. Parameters 1
    through 4, seperated by whitespace, will be groups 3-6.

    Args:
        command: A string, which can be a regular expression.

    Returns:
        A function with a new regular expression appended to the rule
        attribute. If there is no rule attribute, it is added.

    Example:
        @nickname_commands("hello!"):
            Would trigger on "$nickname: hello!", "$nickname,   hello!",
            "$nickname hello!", "$nickname hello! parameter1" and
            "$nickname hello! p1 p2 p3 p4 p5 p6 p7 p8 p9".
        @nickname_commands(".*"):
            Would trigger on anything starting with "$nickname[:,]? ", and
            would have never have any additional parameters, as the command
            would match the rest of the line.

    """
    def add_attribute(function):
        if not hasattr(function, "rule"):
            function.rule = []
        rule = r"""
        ^
        $nickname[:,]? # Nickname.
        \s+({command}) # Command as group 1.
        (?:\s+         # Whitespace to end command.
        (              # Rest of the line as group 2.
        (?:(\S+))?     # Parameters 1-4 as groups 3-6.
        (?:\s+(\S+))?
        (?:\s+(\S+))?
        (?:\s+(\S+))?
        .*             # Accept anything after the parameters. Leave it up to
                       # the module to parse the line.
        ))?            # Group 1 must be None, if there are no parameters.
        $              # EoL, so there are no partial matches.
        """.format(command='|'.join(command_list))
        function.rule.append(rule)
        return function

    return add_attribute


def priority(value):
    """Decorate a function to be executed with higher or lower priority.

    Args:
        value: Priority can be one of "high", "medium", "low". Defaults to
            medium.

    Priority allows you to control the order of callable execution, if your
    module needs it.

    """
    def add_attribute(function):
        function.priority = value
        return function
    return add_attribute


def event(*event_list):
    """Decorate a function to be triggered on specific IRC events.

    This is one of a number of events, such as 'JOIN', 'PART', 'QUIT', etc.
    (More details can be found in RFC 1459.) When the Sopel bot is sent one of
    these events, the function will execute. Note that functions with an event
    must also be given a rule to match (though it may be '.*', which will
    always match) or they will not be triggered.

    :class:`sopel.tools.events` provides human-readable names for many of the
    numeric events, which may help your code be clearer.
    """
    def add_attribute(function):
        if not hasattr(function, "event"):
            function.event = []
        function.event.extend(event_list)
        return function
    return add_attribute


def intent(*intent_list):
    """Decorate a callable trigger on a message with any of the given intents.

    .. versionadded:: 5.2.0
    """
    def add_attribute(function):
        if not hasattr(function, "intents"):
            function.intents = []
        function.intents.extend(intent_list)
        return function
    return add_attribute


def rate(user=0, channel=0, server=0):
    """Decorate a function to limit how often it can be triggered on a per-user
    basis, in a channel, or across the server (bot). A value of zero means no 
    limit. If a function is given a rate of 20, that function may only be used
    once every 20 seconds in the scope corresponding to the parameter.
    Users on the admin list in Sopel’s configuration are exempted from rate 
    limits.

    Rate-limited functions that use scheduled future commands should import
    threading.Timer() instead of sched, or rate limiting will not work properly.
    """
    def add_attribute(function):
        function.rate = user
        function.channel_rate = channel
        function.global_rate = server
        return function
    return add_attribute


def require_privmsg(message=None):
    """Decorate a function to only be triggerable from a private message.

    If it is triggered in a channel message, `message` will be said if given.
    """
    def actual_decorator(function):
        @functools.wraps(function)
        def _nop(*args, **kwargs):
            # Assign trigger and bot for easy access later
            bot, trigger = args[0:2]
            if trigger.is_privmsg:
                return function(*args, **kwargs)
            else:
                if message and not callable(message):
                    bot.say(message)
        return _nop
    # Hack to allow decorator without parens
    if callable(message):
        return actual_decorator(message)
    return actual_decorator


def require_chanmsg(message=None):
    """Decorate a function to only be triggerable from a channel message.

    If it is triggered in a private message, `message` will be said if given.
    """
    def actual_decorator(function):
        @functools.wraps(function)
        def _nop(*args, **kwargs):
            # Assign trigger and bot for easy access later
            bot, trigger = args[0:2]
            if not trigger.is_privmsg:
                return function(*args, **kwargs)
            else:
                if message and not callable(message):
                    bot.say(message)
        return _nop
    # Hack to allow decorator without parens
    if callable(message):
        return actual_decorator(message)
    return actual_decorator


def require_privilege(level, message=None):
    """Decorate a function to require at least the given channel permission.

    `level` can be one of the privilege levels defined in this module. If the
    user does not have the privilege, `message` will be said if given. If it is
    a private message, no checking will be done."""
    def actual_decorator(function):
        @functools.wraps(function)
        def guarded(bot, trigger, *args, **kwargs):
            channel_privs = bot.privileges[trigger.sender]
            allowed = channel_privs.get(trigger.nick, 0) >= level
            if not trigger.is_privmsg and not allowed:
                if message and not callable(message):
                    bot.say(message)
            else:
                return function(bot, trigger, *args, **kwargs)
        return guarded
    return actual_decorator


def require_admin(message=None):
    """Decorate a function to require the triggering user to be a bot admin.

    If they are not, `message` will be said if given."""
    def actual_decorator(function):
        @functools.wraps(function)
        def guarded(bot, trigger, *args, **kwargs):
            if not trigger.admin:
                if message and not callable(message):
                    bot.say(message)
            else:
                return function(bot, trigger, *args, **kwargs)
        return guarded
    # Hack to allow decorator without parens
    if callable(message):
        return actual_decorator(message)
    return actual_decorator


def require_owner(message=None):
    """Decorate a function to require the triggering user to be the bot owner.

    If they are not, `message` will be said if given."""
    def actual_decorator(function):
        @functools.wraps(function)
        def guarded(bot, trigger, *args, **kwargs):
            if not trigger.owner:
                if message and not callable(message):
                    bot.say(message)
            else:
                return function(bot, trigger, *args, **kwargs)
        return guarded
    # Hack to allow decorator without parens
    if callable(message):
        return actual_decorator(message)
    return actual_decorator


class example(object):
    """Decorate a function with an example.

    Add an example attribute into a function and generate a test.
    """
    # TODO dat doc doe >_<
    def __init__(self, msg, result=None, privmsg=False, admin=False,
                 owner=False, repeat=1, re=False, ignore=None):
        """Accepts arguments for the decorator.

        Args:
            msg - The example message to give to the function as input.
            result - Resulting output from calling the function with msg.
            privmsg - If true, make the message appear to have sent in a
                private message to the bot. If false, make it appear to have
                come from a channel.
            admin - Bool. Make the message appear to have come from an admin.
            owner - Bool. Make the message appear to have come from an owner.
            repeat - How many times to repeat the test. Usefull for tests that
                return random stuff.
            re - Bool. If true, result is interpreted as a regular expression.
            ignore - a list of outputs to ignore.

        """
        # Wrap result into a list for get_example_test
        if isinstance(result, list):
            self.result = result
        elif result is not None:
            self.result = [result]
        else:
            self.result = None
        self.use_re = re
        self.msg = msg
        self.privmsg = privmsg
        self.admin = admin
        self.owner = owner
        self.repeat = repeat

        if isinstance(ignore, list):
            self.ignore = ignore
        elif ignore is not None:
            self.ignore = [ignore]
        else:
            self.ignore = []

    def __call__(self, func):
        if not hasattr(func, "example"):
            func.example = []

        if self.result:
            test = sopel.test_tools.get_example_test(
                func, self.msg, self.result, self.privmsg, self.admin,
                self.owner, self.repeat, self.use_re, self.ignore
            )
            sopel.test_tools.insert_into_module(
                test, func.__module__, func.__name__, 'test_example'
            )

        record = {
            "example": self.msg,
            "result": self.result,
            "privmsg": self.privmsg,
            "admin": self.admin,
        }
        func.example.append(record)
        return func
