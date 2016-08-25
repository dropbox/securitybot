from unittest2 import TestCase
from mock import Mock, patch

import yaml
import types
import os.path
import pytz
from datetime import datetime

import securitybot.bot as bot
import securitybot.commands as commands
import securitybot.user
import securitybot.chat.chat

MAIN_CONFIG = 'config/bot.yaml'
COMMAND_CONFIG = 'config/commands.yaml'
MESSAGE_CONFIG = 'config/messages.yaml'

@patch('securitybot.chat.chat.Chat', autospec=True)
def fake_init(self, tasker, auth_builder, reporting_channel, client):
    self.username = 'testing-bot'
    self.tasker = tasker
    self.auth_builder = auth_builder
    self.reporting_channel = reporting_channel
    self._last_task_poll = datetime.min.replace(tzinfo=pytz.utc)
    self._last_report = datetime.min.replace(tzinfo=pytz.utc)

    self.chat = client

    self.users = {}
    self.users_by_name = {}
    self.active_users = {}

    self.commands = {}

    self.messages = {}

bot.SecurityBot.__init__ = fake_init

class ConfigTest(TestCase):
    # Validate configuration files
    def test_config(self):
        '''Tests bot.yaml.'''
        with open(MAIN_CONFIG) as f:
            config = yaml.safe_load(f)
            for path in [s + '_path' for s in ['messages', 'commands']]:
                assert path in config, 'No {0} provided'.format(path.replace('_', ' '))
                # Test that files exist
                assert os.path.isfile(config[path]), '{0} missing'.format(path.replace('_', ' '))

    def test_commands(self):
        '''Tests commands.yaml'''
        with open(COMMAND_CONFIG) as f:
            config = yaml.safe_load(f)
            for name, items in config.items():
                assert 'info' in items, 'No info provided for {0}'.format(name)
                assert 'fn' in items, 'No function provided for {0}'.format(name)
                assert isinstance(getattr(commands, items['fn'], None), types.FunctionType), \
                    '{0}: {1} is not a function'.format(name, items['fn'])

    def test_messages(self):
        '''Tests messages.yaml.'''
        with open(MESSAGE_CONFIG) as f:
            config = yaml.safe_load(f)
            for name, string in config.items():
                assert type(string) is str, 'All messages must be strings.'

class BotMessageTest(TestCase):
    '''
    Tests different kinds of message handling.
    '''
    def setUp(self):
        self.bot = bot.SecurityBot(None, None, None)
        self.bot.messages['bad_command'] = 'bad-command'
        self.bot.users = {'id': {'id': 'id', 'name': 'name'}}

    def test_handle_messages_command(self):
        '''Test receiving a command.'''
        self.bot.commands = {'test': None}
        self.bot.handle_command = Mock()
        self.bot.chat.get_messages.return_value = [{'type': 'message',
                                                    'user': 'id',
                                                    'channel': 'D12345',
                                                    'text': 'test command'}]
        self.bot.handle_messages()
        self.bot.handle_command.assert_called_with(self.bot.users['id'], 'test command')

    def test_handle_messages_not_command(self):
        '''Test receiving a message that isn't a command.'''
        self.bot.commands = {'test': None}
        self.bot.message_user = Mock()
        self.bot.chat.get_messages.return_value = [{'type': 'message',
                                                    'user': 'id',
                                                    'channel': 'D12345',
                                                    'text': 'not a command'}]
        self.bot.handle_messages()
        self.bot.chat.message_user.assert_called_with(self.bot.users['id'], 'bad-command')

    def test_handle_messages_not_dm(self):
        '''Test receiving a message that's not from a DM channel.'''
        self.bot.user_lookup = Mock()
        self.bot.chat.get_messages.return_value = []
        self.bot.handle_messages()
        assert not self.bot.user_lookup.called, 'No user should have been looked up'

class BotCommandTest(TestCase):
    '''
    Tests handling a command.
    '''

    def test_command_success(self):
        b = bot.SecurityBot(None, None, None)
        mock_command = Mock()
        mock_command.return_value = True
        b.commands = {'test': {'fn': mock_command, 'success_msg': 'success_msg'}}
        user = {'id': '123', 'name': 'test-user'}
        b.handle_command(user, 'test command')
        mock_command.assert_called_with(b, user, ['command'])
        b.chat.message_user.assert_called_with(user, 'success_msg')

    def test_command_failure(self):
        b = bot.SecurityBot(None, None, None)
        mock_command = Mock()
        mock_command.return_value = False
        b.commands = {'test': {'fn': mock_command, 'failure_msg': 'failure_msg'}}
        user = {'id': '123', 'name': 'test-user'}
        b.handle_command(user, 'test command')
        mock_command.assert_called_with(b, user, ['command'])
        b.chat.message_user.assert_called_with(user, 'failure_msg')

class BotTaskTest(TestCase):
    '''
    Tests handling of tasks.
    '''

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.tasker.tasker.Tasker', autospec=True)
    def setUp(self, tasker, patch_task):
        self.bot = bot.SecurityBot(tasker, None, None)
        self.bot.greet_user = Mock()
        self.bot.blacklist = Mock()
        self.bot.blacklist.is_present.return_value = False

        self.patch_task = patch_task
        self.task = patch_task.start()
        self.task.title = 'title'
        self.task.username = 'user'
        self.task.comment = ''

        tasker.get_new_tasks.return_value = [self.task]
        tasker.get_pending_tasks.return_value = [self.task]

        self.user = securitybot.user.User({'id': 'id', 'name': 'user'}, None, self.bot)
        self.bot.users_by_name = {'user': self.user}

        import securitybot.ignored_alerts as ignored_alerts
        self.ignored_alerts = ignored_alerts
        ignored_alerts.__update_ignored_list = Mock()
        ignored_alerts.get_ignored = Mock(return_value={})
        ignored_alerts.ignore_task = Mock()

    def tearDown(self):
        self.patch_task.stop()

    def test_new_task(self):
        '''
        Tests receiving a new task that is neither for a blacklisted
        user or an ignored task.
        '''
        self.bot.handle_new_tasks()
        self.bot.greet_user.assert_called_with(self.user)
        assert self.user['id'] in self.bot.active_users

    def test_blacklisted_task(self):
        '''Tests receiving a new task that is blacklisted.'''
        self.bot.blacklist.is_present.return_value = True
        self.bot.handle_new_tasks()
        assert self.task.comment == 'blacklisted'
        self.task.set_verifying.assert_called_with()

    def test_ignored_task(self):
        '''Tests receiving a new task that is ignored by the user.'''
        self.ignored_alerts.get_ignored = Mock(return_value={'title': 'ignored'})
        self.bot.handle_new_tasks()
        assert self.task.comment == 'ignored'
        self.task.set_verifying.assert_called_with()

    def test_no_user_task(self):
        '''Tests a task assigned to an unknown or invalid username.'''
        self.task.username = 'another user'
        self.bot.handle_new_tasks()
        assert self.task.comment == 'invalid user'
        self.task.set_verifying.assert_called_with()

class BotUserTest(TestCase):
    def test_populate(self):
        '''
        Tests populating users.
        '''
        sb = bot.SecurityBot(None, lambda *args: None, None)
        user = {'id': 'id', 'name': 'name'}
        sb._api_call = Mock()
        sb.chat.get_users.return_value = [user]
        sb._populate_users()
        sb.chat.get_users.assert_called_with()
        assert user['id'] in sb.users
        assert user['name'] in sb.users_by_name

    @patch('securitybot.user.User', autospec=True)
    def test_step(self, user):
        '''
        Tests stepping over all users on a user step.
        '''
        sb = bot.SecurityBot(None, None, None)
        sb.active_users = {'key': user}
        sb.handle_users()
        user.step.assert_called_with()

class BotHelperTest(TestCase):
    '''
    Test cases for help functions in the bot that don't require
    actually constructing a bot properly.
    '''

    # User handling tests
    def test_user_lookup(self):
        '''Tests user lookup on ID.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': 'id', 'name': 'user'}
        sb.users = {user['id']: user}
        assert sb.user_lookup('id') == user
        try:
            sb.user_lookup('not-a-real-id')
        except Exception:
            return
        assert False, 'A user should not have been found.'

    def test_user_lookup_by_name(self):
        '''Tests user lookup on ID.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': 'id', 'name': 'user'}
        sb.users_by_name = {user['name']: user}
        assert sb.user_lookup_by_name('user') == user
        try:
            sb.user_lookup_by_name('not-a-real-user')
        except Exception:
            return
        assert False, 'A user should not have been found.'

    def test_valid_user_valid(self):
        '''Tests valid_user with a valid user.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': '1234', 'name': 'mock-user'}
        sb.users = {user['id']: user}
        sb.users_by_name = {user['name']: user}
        assert sb.valid_user('mock-user')

    def test_valid_user_invalid(self):
        '''Tests valid_user with an invalid user.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': '1234', 'name': 'mock-user'}
        sb.users = {user['id']: user}
        sb.users_by_name = {user['name']: user}
        assert not sb.valid_user('fake-user')

    def test_valid_user_malformed(self):
        '''Tests valid_user with a malformed user.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': '1234', 'name': 'mock-user'}
        sb.users = {user['id']: user}
        sb.users_by_name = {user['name']: user}
        assert not sb.valid_user('mock-user\nfake-user')

    def test_valid_user_empty(self):
        '''Tests valid_user with a malformed user.'''
        sb = bot.SecurityBot(None, None, None)
        user = {'id': '1234', 'name': 'mock-user'}
        sb.users = {user['id']: user}
        sb.users_by_name = {user['name']: user}
        assert not sb.valid_user('')

    def test_cleanup_user(self):
        '''
        Test users being cleaned up properly.

        ... or at least the active_users dictionary having an element removed.
        '''
        # We'll mock a user using a dictionary since that's easier...
        user = {'id': '1234', 'name': 'mock-user'}
        fake_user = {'id': '5678', 'name': 'fake-user'}
        sb = bot.SecurityBot(None, None, None)
        sb.active_users = {user['id']: user}
        assert len(sb.active_users) == 1
        sb.cleanup_user(fake_user)
        assert len(sb.active_users) == 1
        sb.cleanup_user(user)
        assert len(sb.active_users) == 0

    # Command parsing tests
    def test_parse_command(self):
        '''Test parsing simple commands.'''
        sb = bot.SecurityBot(None, None, None)
        assert sb.parse_command('command text') == ('command', ['text'])
        assert sb.parse_command('command unquoted text') == ('command', ['unquoted', 'text'])
        assert sb.parse_command('command "quoted text"') == ('command', ['quoted text'])

    def test_parse_punctuation(self):
        '''Test parsing with punctuation in the command.'''
        sb = bot.SecurityBot(None, None, None)
        root = 'command'
        # Minimal set of punctuation to always avoid
        for char in bot.PUNCTUATION:
            assert sb.parse_command(root + char) == (root, [])

    def test_parse_nl_command(self):
        '''Test parsing commands that contain text in natural language.'''
        sb = bot.SecurityBot(None, None, None)
        command = 'command With some language.'
        assert sb.parse_command(command) == ('command', ['With', 'some', 'language.'])
        command = 'command I\'m cool.'
        assert sb.parse_command(command) == ('command', ['I\'m', 'cool.'])

    def test_parse_unicode(self):
        '''Tests parsing a command with unicode.'''
        sb = bot.SecurityBot(None, None, None)
        command = u'command \u2014flag'
        assert sb.parse_command(command) == ('command', ['--flag'])
        command = u'command \u201cquoted text\u201d'
        assert sb.parse_command(command) == ('command', ['quoted text'])
