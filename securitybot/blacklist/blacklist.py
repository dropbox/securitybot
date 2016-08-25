'''
A generic blacklist class.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

from abc import ABCMeta, abstractmethod

class Blacklist(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def is_present(self, name):
        # type: (str) -> bool
        '''
        Checks if a name is on the blacklist.

        Args:
            name (str): The name to check.
        '''
        pass

    @abstractmethod
    def add(self, name):
        # type: (str) -> None
        '''
        Adds a name to the blacklist.

        Args:
            name (str): The name to add to the blacklist.
        '''
        pass

    @abstractmethod
    def remove(self, name):
        # type: (str) -> None
        '''
        Removes a name to the blacklist.

        Args:
            name (str): The name to remove from the blacklist.
        '''
        pass
