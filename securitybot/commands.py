'''
File for securitybot commands.

Each command function takes a user and arguments as its arguments.
It also has `bot`, a reference to the bot that called it.
They return True upon success and False upon failure, or just None
if the command doesn't have success/failure messages.
'''
import re

from datetime import timedelta

import securitybot.ignored_alerts as ignored_alerts
from securitybot.util import create_new_alert

def hi(bot, user, args):
    '''Says hello to a user.'''
    bot.chat.message_user(user, bot.messages['hi'].format(user.get_name()))

def help(bot, user, args):
    '''Prints help for each command.'''
    msg = '{0}\n\n'.format(bot.messages['help_header'])
    for name, info in sorted(bot.commands.items()):
        if not info['hidden'] or '-a' in args:
            msg += '`{0}`: {1}\n'.format(name, info['info'])
            if info['usage']:
                usage_str = '\n'.join(['> \t' + s for s in info['usage']])
                msg += '> {0}:\n{1}\n'.format(bot.messages['help_usage'], usage_str)
    msg += bot.messages['help_footer']
    bot.chat.message_user(user, msg)

def add_to_blacklist(bot, user, args):
    '''Adds a user to the blacklist.'''
    name = user['name']
    if not bot.blacklist.is_present(name):
        bot.blacklist.add(name)
        return True
    return False

def remove_from_blacklist(bot, user, args):
    '''Removes a user from the blacklist.'''
    name = user['name']
    if bot.blacklist.is_present(name):
        bot.blacklist.remove(name)
        return True
    return False

def positive_response(bot, user, args):
    '''Registers a postive response from a user.'''
    user.positive_response(' '.join(args))

def negative_response(bot, user, args):
    '''Registers a negative response from a user.'''
    user.negative_response(' '.join(args))

TIME_REGEX = re.compile(r'([0-9]+h)?([0-9]+m)?', flags=re.IGNORECASE)
OUTATIME = timedelta()
TIME_LIMIT = timedelta(hours=4)

def ignore(bot, user, args):
    '''Ignores a specific alert for a user for some period of time.'''
    if len(args) != 2:
        return False

    which, time = args

    # Find correct task in user object
    task = None
    if which == 'last' and user.old_tasks:
        task = user.old_tasks[-1]
    elif which == 'current' and user.pending_task:
        task = user.pending_task
    if task is None:
        return False

    # Parse given time using above regex
    match = TIME_REGEX.match(time)
    if not (match or match.group(0)):
        return False
    # Parse time returned by regex, snipping off the trailing letter
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    # Build and cap time if needed
    ignoretime = timedelta(hours=hours, minutes=minutes)
    if ignoretime > TIME_LIMIT:
        bot.chat.message_user(user, bot.messages['ignore_time'])
        ignoretime = TIME_LIMIT
    elif ignoretime <= OUTATIME:
        bot.chat.message_user(user, bot.messages['ignore_no_time'])
        return False

    ignored_alerts.ignore_task(user['name'], task.title, 'ignored', ignoretime)
    return True

def test(bot, user, args):
    '''Creates a new test alert in Maniphest for a user.'''
    create_new_alert('testing_alert', user['name'], 'Testing alert', 'Testing Securitybot')

    return True
