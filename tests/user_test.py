from unittest2 import TestCase
from mock import Mock, patch

from collections import defaultdict
from datetime import timedelta

import securitybot.user as user
import securitybot.bot
import securitybot.chat.chat
import securitybot.auth.auth

# Mock away ignoring alerts
import securitybot.ignored_alerts as ignored_alerts
ignored_alerts.__update_ignored_list = Mock()
ignored_alerts.get_ignored = Mock(return_value={})
ignored_alerts.get_ignored.return_value = {}
ignored_alerts.ignore_task = Mock()

class UserTest(TestCase):
    @patch('securitybot.chat.chat.Chat', autospec=True)
    @patch('securitybot.bot.SecurityBot', autospec=True)
    def setUp(self, bot, chat):
        bot.chat = chat
        self.bot = bot

    def test_construction(self):
        '''Tests basic construction of a user.'''
        user.User({}, None, None)

    def test_get_attributes(self):
        '''Tests grabbing attributes like a dictionary.'''
        test_user = user.User({'alphabet': 'soup',
                               'animal': 'crackers'},
                               None, None)
        assert test_user['alphabet'] == 'soup'
        assert test_user['animal'] == 'crackers'

    def test_name(self):
        '''Tests getting a user's name.'''
        test_user = user.User({'profile': {'first_name': 'Bot'}}, None, None)
        assert test_user.get_name() == 'Bot'
        test_user = user.User({'profile': {}, 'name': 'Bot2'}, None, None)
        assert test_user.get_name() == 'Bot2'

    # User interaction flows

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_basic_flow(self, auth, mock_task):
        '''
        Tests basic flow through the bot.
        This is the most basic flow:
            new task => did perform => allow 2FA => valid 2FA => no task
        This will ensure that the states progress as expected and the bot
        cleans itself up afterwards.
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.NONE
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        # Also test not advancing on no queued task
        test_user.step()
        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'auth_permission_check'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'waiting_on_auth'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.AUTHORIZED
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'

        test_user.step()
        self.bot.cleanup_user.assert_called_with(test_user)
        assert str(test_user._fsm.state) == 'need_task'
        task.set_verifying.assert_called_with()

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_did_not_do_flow(self, auth, mock_task):
        '''
        Tests flow if a user did not perform an action.
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.NONE
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        self.bot.reporting_channel = None
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        # Also test not advancing on no queued task
        test_user.step()
        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.negative_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_two_task_flow(self, auth, mock_task):
        '''
        Tests two task. Once the first is completed, the bot should send a
        a message announcing that another task exists.
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.NONE
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)
        test_user.send_message = Mock()

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        # Add two tasks to the queue
        test_user.add_task(task)
        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'auth_permission_check'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'waiting_on_auth'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.AUTHORIZED
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'

        test_user.step()
        test_user.send_message.assert_called_with('bwtm')
        assert str(test_user._fsm.state) == 'need_task'
        task.set_verifying.assert_called_with()

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_already_authorized_flow(self, auth, mock_task):
        '''
        Tests already being authorized after confirming an alert.
        This is the most basic flow:
            new task => did perform => already authorized => no task
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.AUTHORIZED
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.step()
        self.bot.cleanup_user.assert_called_with(test_user)
        assert str(test_user._fsm.state) == 'need_task'
        task.set_verifying.assert_called_with()

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_no_2fa(self, auth, mock_task):
        '''
        Tests a user not having 2FA capability.
        This is the most basic flow:
            new task => did perform => allow 2FA => valid 2FA => no task
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.NONE
        auth.can_auth.return_value = False
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        test_user.step()
        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.step()
        self.bot.cleanup_user.assert_called_with(test_user)
        assert str(test_user._fsm.state) == 'need_task'
        task.set_verifying.assert_called_with()

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_not_allow_2fa_flow(self, auth, mock_task):
        '''
        Tests if the user denies being sent a Duo Push.
        '''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.NONE
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        # Also test not advancing on no queued task
        test_user.step()
        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'auth_permission_check'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.negative_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        mock_task.stop()

    @patch('securitybot.user.ESCALATION_TIME', timedelta(seconds=-1))
    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_auto_escalate(self, auth, mock_task):
        '''Tests that after some time an alert automatically escalates.'''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.DENIED
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        # Auto-escalation should happen immediately because escalation time
        # is set to be zero seconds

        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        task.set_verifying.assert_called_with()

        mock_task.stop()

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_deny_resets_auth(self, auth, mock_task):
        '''Tests that receiving a deny from 2FA resets any saved authorization.'''
        auth.auth_status.return_value = securitybot.auth.auth.AUTH_STATES.DENIED
        auth.can_auth.return_value = True
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)

        task = mock_task.start()

        assert str(test_user._fsm.state) == 'need_task'

        test_user.add_task(task)
        test_user.step()
        assert str(test_user._fsm.state) == 'action_performed_check'

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'auth_permission_check'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.positive_response('Dummy explanation.')
        test_user.step()
        assert str(test_user._fsm.state) == 'waiting_on_auth'
        assert (test_user._last_message.answer is None and
                test_user._last_message.text == '')

        test_user.step()
        assert str(test_user._fsm.state) == 'task_finished'
        auth.reset.assert_called_with()

        mock_task.stop()

    # Auth interactions

    @patch('securitybot.tasker.tasker.Task')
    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_start_auth(self, auth, mock_task):
        '''Tests that authorization calls call the auth object.'''
        self.bot.messages = defaultdict(str)
        test_user = user.User({}, auth, self.bot)
        task = mock_task.start()

        test_user.pending_task = task
        test_user.begin_auth()
        auth.auth.assert_called_with(task.description)

        mock_task.stop()

    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_check_auth(self, auth):
        '''Tests that auth status calls interact properly.'''
        test_user = user.User({}, auth, None)

        test_user.auth_status()
        auth.auth_status.assert_called_with()

    @patch('securitybot.auth.auth.Auth', autospec=True)
    def test_reset_auth(self, auth):
        '''Tests that auth is properly reset on `reset_auth`.'''
        test_user = user.User({}, auth, None)

        test_user.reset_auth()
        auth.reset.assert_called_with()
