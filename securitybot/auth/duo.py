'''
Authentication using Duo.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

import logging
from datetime import datetime
from urllib import urlencode
from securitybot.auth.auth import Auth, AUTH_STATES, AUTH_TIME

from typing import Any

class DuoAuth(Auth):
    def __init__(self, duo_api, username):
        # type: (Any, str) -> None
        '''
        Args:
            duo_api (duo_client.Auth): An Auth API client from Duo.
            username (str): The username of the person authorized through
                            this object.
        '''
        self.client = duo_api
        self.username = username
        self.txid = None # type: str
        self.auth_time = datetime.min
        self.state = AUTH_STATES.NONE

    def can_auth(self):
        # type: () -> bool
        # Use Duo preauth to look for a device with Push
        # TODO: This won't work for anyone who's set to auto-allow, but
        # I don't believe we have anyone like that...
        logging.debug('Checking auth capabilities for {}'.format(self.username))
        res = self.client.preauth(username=self.username)
        if res['result'] == 'auth':
            for device in res['devices']:
                if 'push' in device['capabilities']:
                    return True
        return False

    def auth(self, reason=None):
        # type: (str) -> None
        logging.debug('Sending Duo Push request for {}'.format(self.username))
        pushinfo = 'from=Securitybot'
        if reason:
            pushinfo += '&'
            pushinfo += urlencode({'reason': reason})

        res = self.client.auth(
            username=self.username,
            async=True,
            factor='push',
            device='auto',
            type='Securitybot',
            pushinfo=pushinfo
        )
        self.txid = res['txid']
        self.state = AUTH_STATES.PENDING

    def _recently_authed(self):
        # type: () -> bool
        return (datetime.now() - self.auth_time) < AUTH_TIME

    def auth_status(self):
        # type: () -> int
        if self.state == AUTH_STATES.PENDING:
            res = self.client.auth_status(self.txid)
            if not res['waiting']:
                if res['success']:
                    self.state = AUTH_STATES.AUTHORIZED
                    self.auth_time = datetime.now()
                else:
                    self.state = AUTH_STATES.DENIED
                    self.auth_time = datetime.min
        elif self.state == AUTH_STATES.AUTHORIZED:
            if not self._recently_authed():
                self.state = AUTH_STATES.NONE
        return self.state

    def reset(self):
        # type: () -> None
        self.txid = None
        self.state = AUTH_STATES.NONE
