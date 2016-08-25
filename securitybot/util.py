__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

import pytz
import binascii
import os
from datetime import datetime, timedelta
from collections import namedtuple

from securitybot.sql import SQLEngine

# http://stackoverflow.com/questions/36932/how-can-i-represent-an-enum-in-python
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def tuple_builder(answer=None, text=None):
    tup = namedtuple('Response', ['answer', 'text'])
    tup.answer = answer if answer is not None else None
    tup.text = text if text is not None else ''
    return tup

OPENING_HOUR = 10
CLOSING_HOUR = 18
LOCAL_TZ = pytz.timezone('America/Los_Angeles')

def during_business_hours(time):
    '''
    Checks if a given time is within business hours. Currently is true
    from 10:00 to 17:59. Also checks to make sure that the day is a weekday.

    Args:
        time (Datetime): A datetime object to check.
    '''
    if time.tzinfo is not None:
        here = time.astimezone(LOCAL_TZ)
    else:
        here = time.replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ)
    return (OPENING_HOUR <= here.hour < CLOSING_HOUR and
            1 <= time.isoweekday() <= 5)

def get_expiration_time(start, time):
    '''
    Gets an expiration time for an alert.
    Works by adding on a certain time and wrapping around after business hours
    so that alerts that are started near the end of the day don't expire.

    Args:
        start (Datetime): A datetime object indicating when an alert was started.
        time (Timedelta): A timedelta representing the amount of time the alert
            should live for.
    Returns:
        Datetime: The expiry time for an alert.
    '''
    if start.tzinfo is None:
        start = start.replace(tzinfo=pytz.utc)
    end = start + time
    if not during_business_hours(end):
        end_of_day = datetime(year=start.year,
                              month=start.month,
                              day=start.day,
                              hour=CLOSING_HOUR,
                              tzinfo=LOCAL_TZ)
        delta = end - end_of_day
        next_day = end_of_day + timedelta(hours=(OPENING_HOUR - CLOSING_HOUR) % 24)
        # This may land on a weekend, so march to the next weekday
        while not during_business_hours(next_day):
            next_day += timedelta(days=1)
        end = next_day + delta
    return end

def create_new_alert(title, ldap, description, reason, url='N/A', key=None):
    # type: (str, str, str, str, str, str) -> None
    '''
    Creates a new alert in the SQL DB with an optionally random hash.
    '''
    # Generate random key if none provided
    if key is None:
        key = binascii.hexlify(os.urandom(32))

    # Insert that into the database as a new alert
    SQLEngine.execute('''
    INSERT INTO alerts (hash, ldap, title, description, reason, url, event_time)
    VALUES (UNHEX(%s), %s, %s, %s, %s, %s, NOW())
    ''',
    (key, ldap, title, description, reason, url))

    SQLEngine.execute('''
    INSERT INTO user_responses (hash, comment, performed, authenticated)
    VALUES (UNHEX(%s), '', false, false)
    ''',
    (key,))

    SQLEngine.execute('INSERT INTO alert_status (hash, status) VALUES (UNHEX(%s), 0)',
                      (key,))
