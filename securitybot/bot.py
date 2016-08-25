'''
The internals of securitybot. Defines a core class SecurityBot that manages
most of the bot's behavior.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

import logging
from securitybot.user import User
import time
from datetime import datetime, timedelta
import pytz
import shlex
import yaml
import string

import securitybot.commands as bot_commands
from securitybot.blacklist.sql_blacklist import SQLBlacklist
from securitybot.chat.chat import Chat
from securitybot.tasker.tasker import Task, Tasker
from securitybot.auth.auth import Auth

from typing import Any, Callable, Dict, List, Tuple

TASK_POLL_TIME = timedelta(minutes=1)
REPORTING_TIME = timedelta(hours=1)

DEFAULT_COMMAND = {
    'fn': lambda b, u, a: logging.warn('No function provided for this command.'),
    'info': 'I was too lazy to provide information for this command',
    'hidden': False,
    'usage': None,
    'success_msg': None,
    'failure_msg': None,
}

def clean_input(text):
    # type: (unicode) -> str
    '''
    Cleans some input text, doing things such as removing smart quotes.
    '''
    # Replaces smart quotes; Shlex crashes if it encounters an unbalanced
    # smart quote, as happens with auto-formatting.
    text = (text.replace(u'\u2018', '\'')
                .replace(u'\u2019', '\'')
                .replace(u'\u201c','"')
                .replace(u'\u201d', '"'))
    # Undo autoformatting of dashes
    text = (text.replace(u'\u2013', '--')
                .replace(u'\u2014', '--'))

    return text.encode('utf-8')

PUNCTUATION = '.,!?\'"`'

def clean_command(command):
    # type: (str) -> str
    '''Cleans a command.'''
    command = command.lower()
    # Force to str
    command = command.encode('utf-8')
    # Remove punctuation people are likely to use and won't interfere with command names
    command = command.translate(string.maketrans('', ''), PUNCTUATION)
    return command

class SecurityBot(object):
    '''
    It's always dangerous naming classes the same name as the project...
    '''

    def __init__(self, chat, tasker, auth_builder, reporting_channel, config_path):
        # type: (Chat, Tasker, Callable[[str], Auth], str, str) -> None
        '''
        Args:
            chat (Chat): The chat object to use for messaging.
            tasker (Tasker): The Tasker object to get tasks from
            auth_builder (Auth): The constructor to build Auth objects from.
                                 It should take in only a username as a parameter.
            reporting_channel (str): Channel ID to report alerts in need of verification to.
            config_path (str): Path to configuration file
        '''
        logging.info('Creating securitybot.')
        self.tasker = tasker
        self.auth_builder = auth_builder
        self.reporting_channel = reporting_channel
        self._last_task_poll = datetime.min.replace(tzinfo=pytz.utc)
        self._last_report = datetime.min.replace(tzinfo=pytz.utc)

        self._load_config(config_path)

        self.chat = chat
        chat.connect()

        # Load blacklist from SQL
        self.blacklist = SQLBlacklist()

        # A dictionary to be populated with all members of the team
        self.users = {} # type: Dict[str, User]
        self.users_by_name = {} # type: Dict[str, User]
        self._populate_users()

        # Dictionary of users who have outstanding tasks
        self.active_users = {} # type: Dict[str, User]

        # Recover tasks
        self.recover_in_progress_tasks()

        logging.info('Done!')

    # Initialization functions

    def _load_config(self, config_path):
        # type: (str) -> None
        '''
        Loads a configuration file for the bot.
        '''
        logging.info('Loading configuration.')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

            # Required parameters
            try:
                self._load_messages(config['messages_path'])
                self._load_commands(config['commands_path'])
            except KeyError as e:
                logging.error('Missing parameter: {0}'.format(e))
                raise SecurityBotException('Configuration file missing parameters.')

            # Optional parameters
            self.icon_url = config.get('icon_url', 'https://placehold.it/256x256')

    def _load_messages(self, messages_path):
        # type: (str) -> None
        '''
        Loads messages from a YAML file.

        Args:
            messages_path (str): Path to messages file.
        '''
        self.messages = yaml.safe_load(open(messages_path))

    def _load_commands(self, commands_path):
        # type: (str) -> None
        '''
        Loads commands from a configuration file.

        Args:
            commands_path (str): Path to commands file.
        '''
        with open(commands_path, 'r') as f:
            commands = yaml.safe_load(f)

            self.commands = {} # type: Dict[str, Any]
            for name, cmd in commands.items():
                new_cmd = DEFAULT_COMMAND.copy()
                new_cmd.update(cmd)

                try:
                    new_cmd['fn'] = getattr(bot_commands, format(cmd['fn']))
                except AttributeError as e:
                    raise SecurityBotException('Invalid function: {0}'.format(e))

                self.commands[name] = new_cmd
        logging.info('Loaded commands: {0}'.format(self.commands.keys()))

    # Bot functions

    def run(self):
        # type: () -> None
        '''
        Main loop for the bot.
        '''
        while True:
            now = datetime.now(tz=pytz.utc)
            if now - self._last_task_poll > TASK_POLL_TIME:
                self._last_task_poll = now
                self.handle_new_tasks()
                self.handle_in_progress_tasks()
                self.handle_verifying_tasks()
            self.handle_messages()
            self.handle_users()
            time.sleep(.1)

    def handle_messages(self):
        # type: () -> None
        '''
        Handles all messages sent to securitybot.
        Currently only active users are considered, i.e. we don't care if a user
        sends us a message but we haven't sent them anything.
        '''
        messages = self.chat.get_messages()
        for message in messages:
            user_id = message['user']
            text = message['text']
            user = self.user_lookup(user_id)

            # Parse each received line as a command, otherwise send an error message
            if self.is_command(text):
                self.handle_command(user, text)
            else:
                self.chat.message_user(user, self.messages['bad_command'])

    def handle_command(self, user, command):
        # type: (User, str) -> None
        '''
        Handles a given command from a user.
        '''
        key, args = self.parse_command(command)
        logging.info('Handling command {0} for {1}'.format(key, user['name']))
        cmd = self.commands[key]
        if cmd['fn'](self, user, args):
            if cmd['success_msg']:
                self.chat.message_user(user, cmd['success_msg'])
        else:
            if cmd['failure_msg']:
                self.chat.message_user(user, cmd['failure_msg'])

    def valid_user(self, username):
        # type: (str) -> bool
        '''
        Validates a username to be valid.
        '''
        if len(username.split()) != 1:
            return False
        try:
            self.user_lookup_by_name(username)
            return True
        except SecurityBotException as e:
            logging.warn('{}'.format(e))
            return False

    def _add_task(self, task):
        # type: (Task) -> None
        '''
        Adds a new task to the user specified by that task.

        Args:
            task (Task): the task to add.
        '''
        username = task.username
        if self.valid_user(username):
            # Ignore blacklisted users
            if self.blacklist.is_present(username):
                logging.info('Ignoring task for blacklisted {0}'.format(username))
                task.comment = 'blacklisted'
                task.set_verifying()
            else:
                user = self.user_lookup_by_name(username)
                user_id = user['id']
                if user_id not in self.active_users:
                    logging.debug('Adding {} to active users'.format(username))
                    self.active_users[user_id] = user
                    self.greet_user(user)
                user.add_task(task)
                task.set_in_progress()
        else:
            # Escalate if no valid user is found
            logging.warn('Invalid user: {0}'.format(username))
            task.comment = 'invalid user'
            task.set_verifying()

    def handle_new_tasks(self):
        # type: () -> None
        '''
        Handles all new tasks.
        '''
        for task in self.tasker.get_new_tasks():
            # Log new task
            logging.info('Handling new task for {0}'.format(task.username))

            self._add_task(task)

    def handle_in_progress_tasks(self):
        # type: () -> None
        '''
        Handles all in progress tasks.
        '''
        pass

    def recover_in_progress_tasks(self):
        # type: () -> None
        '''
        Recovers in progress tasks from a previous run.
        '''
        for task in self.tasker.get_active_tasks():
            # Log new task
            logging.info('Recovering task for {0}'.format(task.username))

            self._add_task(task)


    def handle_verifying_tasks(self):
        # type: () -> None
        '''
        Handles all tasks which are currently waiting for verification.
        '''
        pass

    def handle_users(self):
        # type: () -> None
        '''
        Handles all users.
        '''
        for user_id in self.active_users.keys():
            user = self.active_users[user_id]
            user.step()

    def cleanup_user(self, user):
        # type: (User) -> None
        '''
        Cleanup a user from the active users list once they have no remaining
        tasks.
        '''
        logging.debug('Removing {} from active users'.format(user['name']))
        self.active_users.pop(user['id'], None)

    def alert_user(self, user, task):
        # type: (User, Task) -> None
        '''
        Alerts a user about an alert that was trigged and associated with their
        name.

        Args:
            user (User): The user associated with the task.
            task (Task): A task to alert on.
        '''
        # Format the reason to be indented
        reason = '\n'.join(['>' + s for s in task.reason.split('\n')])

        message = self.messages['alert'].format(task.description, reason)
        message += '\n'
        message += self.messages['action_prompt']
        self.chat.message_user(user, message)

    # User creation and lookup methods

    def _populate_users(self):
        # type: () -> None
        '''
        Populates the members dictionary mapping user IDs to username, avatar,
        etc.
        '''
        logging.info('Gathering information about all team members...')
        members = self.chat.get_users()
        for member in members:
            user = User(member, self.auth_builder(member['name']), self)
            self.users[member['id']] = user
            self.users_by_name[member['name']] = user
        logging.info('Gathered info on {} users.'.format(len(self.users)))

    def user_lookup(self, id):
        # type: (str) -> User
        '''
        Looks up a user by their ID.

        Args:
            id (str): The ID of a user to look up, formatted like U12345678.
        Returns:
            (dict): All known information about that user.
        '''
        if id not in self.users:
            raise SecurityBotException('User {} not found'.format(id))
        return self.users[id]

    def user_lookup_by_name(self, username):
        # type: (str) -> User
        '''
        Looks up a user by their username.

        Args:
            username (str): The username of the user to look up.
        Resturns:
            (dict): All known information about that user.
        '''
        if username not in self.users_by_name:
            raise SecurityBotException('User {} not found'.format(username))
        return self.users_by_name[username]

    # Chat methods

    def greet_user(self, user):
        # type: (User) -> None
        '''
        Sends a greeting message to a user.

        Args:
            user (User): The user to greet.
        '''
        self.chat.message_user(user, self.messages['greeting'].format(user.get_name()))

    # Command functions
    def is_command(self, command):
        # type: (str) -> bool
        '''Checks if a raw command is a command.'''
        return clean_command(command.split()[0]) in self.commands

    def parse_command(self, command):
        # type: (str) -> Tuple[str, List[str]]
        '''
        Parses a given command.

        Args:
            command (str): The raw command to parse.
        Returns:
            (str, List[str]): A tuple of the command followed by arguments.
        '''
        # First try shlex
        command = clean_input(command)
        try:
            split = shlex.split(command)
        except ValueError:
            # ignore shlex exception
            # Fall back to naive method
            split = command.split()

        return (clean_command(split[0]), split[1:])

class SecurityBotException(Exception):
    pass
