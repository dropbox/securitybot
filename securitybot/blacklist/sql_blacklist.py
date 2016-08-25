'''
A MySQL-based blacklist class.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

from securitybot.blacklist.blacklist import Blacklist
from securitybot.sql import SQLEngine

class SQLBlacklist(Blacklist):
    def __init__(self):
        # type: () -> None
        '''
        Creates a new blacklist tied to a table named "blacklist".
        '''
        # Load from table
        names = SQLEngine.execute('SELECT * FROM blacklist')
        # Break tuples into names
        self._blacklist = {name[0] for name in names}

    def is_present(self, name):
        # type: (str) -> bool
        '''
        Checks if a name is on the blacklist.

        Args:
            name (str): The name to check.
        '''
        return name in self._blacklist

    def add(self, name):
        # type: (str) -> None
        '''
        Adds a name to the blacklist.

        Args:
            name (str): The name to add to the blacklist.
        '''
        self._blacklist.add(name)
        SQLEngine.execute('INSERT INTO blacklist (ldap) VALUES (%s)', (name,))

    def remove(self, name):
        # type: (str) -> None
        '''
        Removes a name to the blacklist.

        Args:
            name (str): The name to remove from the blacklist.
        '''
        self._blacklist.remove(name)
        SQLEngine.execute('DELETE FROM blacklist WHERE ldap = %s', (name,))
