from unittest2 import TestCase

from securitybot.state_machine import StateMachine, StateMachineException

# Helper junk
class Helper(object):
    def __init__(self):
        self.x = 0

    def increment(self):
        self.x += 1

    def x_is_five(self):
        return self.x == 5

class Helper2(object):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0

    def increment_x(self):
        self.x += 1

    def x_at_least_two(self):
        return self.x >= 2

    def increment_y(self):
        self.y += 5

    def increment_z(self):
        self.z += 10

class FSMTest(TestCase):
    # Functionality tests

    def test_simple_chain(self):
        '''Test most basic transition chain.'''
        states = ['one', 'two', 'three']
        transitions = [
            {'source': 'one', 'dest': 'two'},
            {'source': 'two', 'dest': 'three'},
            {'source': 'three', 'dest': 'one'},
        ]
        sm = StateMachine(states, transitions, 'one')
        assert(str(sm.state) == 'one')
        sm.step()
        assert(str(sm.state) == 'two')
        sm.step()
        assert(str(sm.state) == 'three')
        sm.step()
        assert(str(sm.state) == 'one')

    def test_simple_during(self):
        '''Tests a simple action being performed while in a state.'''
        helper = Helper()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two'},
            {'source': 'two', 'dest': 'one'},
        ]
        during = {
            'one': helper.increment
        }
        sm = StateMachine(states, transitions, 'one', during=during)
        assert(helper.x == 0)
        sm.step()
        assert(helper.x == 1)
        sm.step()
        assert(helper.x == 1)

    def test_simple_on_enter(self):
        '''Tests a simple action being performed entering into a state.'''
        helper = Helper()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two'},
            {'source': 'two', 'dest': 'one'},
        ]
        on_enter = {
            'two': helper.increment
        }
        sm = StateMachine(states, transitions, 'one', on_enter=on_enter)
        assert(helper.x == 0)
        sm.step()
        assert(helper.x == 1)
        sm.step()
        assert(helper.x == 1)

    def test_simple_on_exit(self):
        '''Tests a simple action being performed exiting from a state.'''
        helper = Helper()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two'},
            {'source': 'two', 'dest': 'one'},
        ]
        on_exit = {
            'one': helper.increment
        }
        sm = StateMachine(states, transitions, 'one', on_exit=on_exit)
        assert(helper.x == 0)
        sm.step()
        assert(helper.x == 1)
        sm.step()
        assert(helper.x == 1)

    def test_simple_condition(self):
        '''Tests a simple condition check before transitioning.'''
        helper = Helper()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two', 'condition': helper.x_is_five},
            {'source': 'two', 'dest': 'one'},
        ]
        during = {
            'one': helper.increment
        }
        sm = StateMachine(states, transitions, 'one', during=during)
        for x in range(5):
            assert(helper.x == x)
            assert(str(sm.state) == 'one')
            sm.step()
        assert(helper.x == 5)
        assert(str(sm.state) == 'two')
        sm.step()
        assert(helper.x == 5)
        assert(str(sm.state) == 'one')
        sm.step()
        assert(helper.x == 6)
        assert(str(sm.state) == 'one')
        sm.step()
        assert(helper.x == 7)
        assert(str(sm.state) == 'one')

    def test_simple_action(self):
        '''Tests a simple action being performed upon transitioning.'''
        helper = Helper()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two', 'action': helper.increment},
            {'source': 'two', 'dest': 'one'}
        ]
        sm = StateMachine(states, transitions, 'one')
        assert(helper.x == 0)
        assert(str(sm.state) == 'one')
        sm.step()
        assert(helper.x == 1)
        assert(str(sm.state) == 'two')

    def test_correct_state_actions(self):
        '''
        Tests that durings, on_enters, and on_exits are called correctly and
        don't interfere with one another.
        '''
        helper = Helper2()
        states = ['one', 'two']
        transitions = [
            {'source': 'one', 'dest': 'two', 'condition': helper.x_at_least_two},
            {'source': 'two', 'dest': 'one'}
        ]
        during = {
            'one': helper.increment_x
        }
        on_enter = {
            'one': helper.increment_y
        }
        on_exit = {
            'one': helper.increment_z
        }
        sm = StateMachine(states, transitions, 'one', during=during, on_enter=on_enter,
                          on_exit=on_exit)
        sm.step()
        assert(helper.x == 1)
        assert(helper.y == 0)
        assert(helper.z == 0)
        sm.step()
        assert(helper.x == 2)
        assert(helper.y == 0)
        assert(helper.z == 10)
        sm.step()
        assert(helper.x == 2)
        assert(helper.y == 5)
        assert(helper.z == 10)

    # Invalid input error notification tests

    def test_duplicate_states(self):
        states = ['one', 'one']
        try:
            StateMachine(states, {}, 'one')
        except StateMachineException:
            return
        assert False, "No exception thrown on duplicate state names."

    def test_invalid_initial_state(self):
        try:
            StateMachine([], {}, 'foo')
        except StateMachineException:
            return
        assert False, "No exception thrown on invalid initial state name."

    def test_invalid_transition_source_name(self):
        states = ['one']
        transitions = [
            {'source': 'foo', 'dest': 'one'}
        ]
        try:
            StateMachine(states, transitions, 'one')
        except StateMachineException:
            return
        assert False, "No exception thrown on invalid transition source name."

    def test_invalid_transition_dest_name(self):
        states = ['one']
        transitions = [
            {'source': 'one', 'dest': 'foo'}
        ]
        try:
            StateMachine(states, transitions, 'one')
        except StateMachineException:
            return
        assert False, "No exception thrown on invalid transition source name."
