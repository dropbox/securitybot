'''
A simple wrapper over an abstract chat/messaging system
like Slack.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

from securitybot.user import User
from abc import ABCMeta, abstractmethod

from typing import Any, Dict, List

class Chat(object):
    '''
    A wrapper over various chat frameworks, like Slack.
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def connect(self):
        # type: () -> None
        '''Connects to the chat system.'''
        pass

    @abstractmethod
    def get_users(self):
        # type: () -> List[Dict[str, Any]]
        '''
        Returns a list of all users in the chat system.

        Returns:
            A list of dictionaries, each dictionary representing a user.
            The rest of the bot expects the following minimal format:
            {
                "name": The username of a user,
                "id": A user's unique ID in the chat system,
                "profile": A dictionary representing a user with at least:
                    {
                        "first_name": A user's first name
                    }
            }
        '''
        pass

    @abstractmethod
    def get_messages(self):
        # type () -> List[Dict[str, Any]]
        '''
        Gets a list of all new messages received by the bot in direct
        messaging channels. That is, this function ignores all messages
        posted in group chats as the bot never interacts with those.

        Each message should have the following format, minimally:
        {
            "user": The unique ID of the user who sent a message.
            "text": The text of the received message.
        }
        '''
        pass

    @abstractmethod
    def send_message(self, channel, message):
        # type: (Any, str) -> None
        '''
        Sends some message to a desired channel.
        As channels are possibly chat-system specific, this function has a horrible
        type signature.
        '''
        pass

    @abstractmethod
    def message_user(self, user, message):
        # type: (User, str) -> None
        '''
        Sends some message to a desired user, using a User object and a string message.
        '''
        pass

class ChatException(Exception):
    pass
