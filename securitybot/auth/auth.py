'''
An authentication object for doing 2FA on Slack users.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

from securitybot.util import enum
from datetime import timedelta
from abc import ABCMeta, abstractmethod

AUTH_STATES = enum('NONE',
                   'PENDING',
                   'AUTHORIZED',
                   'DENIED',
)

# Allowable time before 2FA is checked again.
# Ideally this should be as low as possible without being annoying.
AUTH_TIME = timedelta(hours=2)

class Auth(object):
    '''
    When designing Auth subclasses, try to make sure that the authorization
    attempt is as non-blocking as possible.
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def can_auth(self):
        # type: () -> bool
        '''
        Returns:
            (bool) Whether 2FA is available.
        '''
        pass

    @abstractmethod
    def auth(self, reason=None):
        # type: (str) -> None
        '''
        Begins an authorization request, which should be non-blocking.

        Args:
            reason (str): Optional reason string that may be provided
        '''
        pass

    @abstractmethod
    def auth_status(self):
        # type: () -> int
        '''
        Returns:
            (enum) The current auth status, one of AUTH_STATES.
        '''
        pass

    @abstractmethod
    def reset(self):
        # type: () -> None
        '''
        Resets auth status.
        '''
        pass
