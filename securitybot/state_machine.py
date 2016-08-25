'''
A simple FSM for controlling user state.
You know, as opposed to all those state machines that _don't_ manage state.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

import logging
from collections import defaultdict

from typing import Callable

class StateMachine(object):
    '''
    A minimal state machine with the ability to declare state transition
    conditions, functions to call when entering and exiting any state, and
    functions to call while in any particular state. All of this is done
    through a single `step` function, which performs all tasks and potentially
    advances to the next state if a condition is met.

    Essentially, this state machine is "eager", it always wants to transition
    to the next state if possible. You could make a main loop out of simply
    chaining state together with various conditions, but this would probably
    make for a terrible UI state machine.
    '''

    def __init__(self, states, transitions, initial, during=None, on_enter=None,
                 on_exit=None):
        '''
        Creates a new state machine. The `during`, `on_enter`, and `on_exit`
        dictionaries are all optional. Additionally, each is free to have
        as few or as many of each state as desired, i.e. leaving out states
        is fine.
        Args:
            states (List[str]): A list of all possible states in the FSM.
            transitions (List[Dict[str, function]]): Dictionaries of transitions
                and conditions. Each dictionary must contain the following keys:
                    source (str): The source state of the transition.
                    dest (str): The destination state of the transition.
                Each dictionary may contain the following keys:
                    condition (function): A condition that must be true for the
                        transition to occur. If no condition is provided then the
                        state machine will transition on a step.
                    action (function): A function to be executed while the
                        transition occurs.
            during (Dict[str, function]): A mapping of states to functions to
                execute while in that state.
            initial (str): The state to start in.
            on_enter (Dict[str, function]): A mapping of states to functions to
                execute when entering that state.
            on_exit (Dict[str, function]): A mapping of states to functions to
                execute when exiting from that state.
        '''
        if during is None:
            during = {}
        if on_enter is None:
            on_enter = {}
        if on_exit is None:
            on_exit = {}

        # Build states
        if sorted(list(set(states))) != sorted(states):
            raise StateMachineException('Duplicate state names encountered:\n{0}'.format(states))

        self._states = {}
        for state in states:
            self._states[state] = State(state,
                                        during.get(state, None),
                                        on_enter.get(state, None),
                                        on_exit.get(state, None)
                                        )

        # Set initial state
        if initial not in self._states:
            raise StateMachineException('Invalid initial state: {0}'.format(initial))
        self.state = self._states[initial]

        # Build transitions
        self._transitions = defaultdict(list)
        for transition in transitions:
            # Validate transition for correct states
            if transition['source'] not in self._states:
                raise StateMachineException('Invalid source state: {0}'
                    .format(transition['source']))
            if transition['dest'] not in self._states:
                raise StateMachineException('Invalid destination state: {0}'
                    .format(transition['dest']))

            source_state = self._states[transition['source']]
            dest_state = self._states[transition['dest']]
            self._transitions[transition['source']].append(Transition(source_state,
                                                               dest_state,
                                                               transition.get('condition', None),
                                                               transition.get('action', None)
                                                               ))

    def step(self):
        # type: () -> None
        '''
        Performs a step in the state machine.
        Each step iterates over the current state's `during` function then checks all
        possible transition paths, evaluates their condition, and transitions if possible.
        The next state is which transition condition was true first or the current state
        if no conditions were true.
        '''
        self.state.during()

        for transition in self._transitions[self.state.name]:
            if transition.condition():
                logging.debug('Transitioning: {0}'.format(transition))
                transition.action()
                self.state.on_exit()
                self.state = transition.dest
                self.state.on_enter()
                break

class State(object):
    '''
    A simple representation of a state in `StateMachine`.
    Each state has a function to perform while it's active, when it's entered
    into, and when it's exited. These functions may be None.
    '''
    def __init__(self, name, during, on_enter, on_exit):
        # type: (str, Callable[..., None], Callable[..., None], Callable[..., None]) -> None
        '''
        Args:
            name (str): The name of this state.
            during (function): A function to call while this state is active.
            on_enter (function): A function to call when transitioning into
                                 this state.
            on_exit (function): A function to call when transitioning out of
                                this state.
        '''
        self.name = name
        self._during = during
        self._on_enter = on_enter
        self._on_exit = on_exit

    def __repr__(self):
        # type: () -> str
        return "State({0}, {1}, {2}, {3})".format(self.name,
                                                  self._during,
                                                  self._on_enter,
                                                  self._on_exit
                                                  )

    def __str__(self):
        # type: () -> str
        return self.name

    def during(self):
        # type: () -> None
        if self._during is not None:
            self._during()

    def on_enter(self):
        # type: () -> None
        if self._on_enter is not None:
            self._on_enter()

    def on_exit(self):
        # type: () -> None
        if self._on_exit is not None:
            self._on_exit()

class Transition(object):
    '''
    A transition object to move between states. Each transition object holds
    a reference to its source and destination states, as well as the condition
    function it requires for transitioning and the action to perform upon
    transitioning.
    '''

    def __init__(self, source, dest, condition, action):
        # type: (State, State, Callable[..., bool], Callable[..., None]) -> None
        '''
        Args:
            source (State): The source State for this transition.
            dest (State): The destination State for this transition.
            condition (function): The transitioning condition callback.
            action (function): An action to perform upon transitioning.
        '''
        self.source = source
        self.dest = dest
        self._condition = condition
        self._action = action

    def __repr__(self):
        # type: () -> str
        return "Transition({0}, {1}, {2}, {3})".format(repr(self.source),
                                                       repr(self.dest),
                                                       self._condition,
                                                       self._action
                                                       )

    def __str__(self):
        # type: () -> str
        return "{0} => {1}".format(self.source, self.dest)

    def condition(self):
        # type: () -> bool
        # Conditions default to True if none is provided
        return True if self._condition is None else self._condition()

    def action(self):
        # type: () -> None
        if self._action is not None:
            self._action()

class StateMachineException(Exception):
    pass
