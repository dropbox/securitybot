'''
A small file for keeping track of ignored alerts in the database.
'''
import pytz
from datetime import datetime, timedelta
from securitybot.sql import SQLEngine
from typing import Dict

def __update_ignored_list():
    # type: () -> None
    '''
    Prunes the ignored table of old ignored alerts.
    '''
    SQLEngine.execute('''DELETE FROM ignored WHERE until <= NOW()''')

def get_ignored(username):
    # type: (str) -> Dict[str, str]
    '''
    Returns a dictionary of ignored alerts to reasons why
    the ignored are ignored.

    Args:
        username (str): The username of the user to retrieve ignored alerts for.
    Returns:
        Dict[str, str]: A mapping of ignored alert titles to reasons
    '''
    __update_ignored_list()
    rows = SQLEngine.execute('''SELECT title, reason FROM ignored WHERE ldap = %s''', (username,))
    return {row[0]: row[1] for row in rows}

def ignore_task(username, title, reason, ttl):
    # type: (str, str, str, timedelta) -> None
    '''
    Adds a task with the given title to the ignore list for the given
    amount of time. Additionally adds an optional message to specify the
    reason that the alert was ignored.

    Args:
        username (str): The username of the user to ignore the given alert for.
        title (str): The title of the alert to ignore.
        ttl (Timedelta): The amount of time to ignore the alert for.
        msg (str): An optional string specifying why an alert was ignored
    '''
    expiry_time = datetime.now(tz=pytz.utc) + ttl
    # NB: Non-standard MySQL specific query
    SQLEngine.execute('''INSERT INTO ignored (ldap, title, reason, until)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE reason=VALUES(reason), until=VALUES(until)
    ''', (username, title, reason, expiry_time.strftime('%Y-%m-%d %H:%M:%S')))
