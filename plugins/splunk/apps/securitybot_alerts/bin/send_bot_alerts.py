#!/usr/local/env python

import sys
import csv
import gzip
import logging

import json

from securitybot.sql import SQLEngine, init_sql
from securitybot.util import create_new_alert

def create_securitybot_task(search_name, hash, username, description, reason, url):
    '''
    Creates a new Maniphest task with the securitybot tag so that the bot can
    reach out to the relevant people.
    '''
    logging.info('Creating new task about {} for {}'.format(description,
                                                            username))

    # Check for collision
    rows = SQLEngine.execute('SELECT title FROM alerts WHERE hash=UNHEX(%s)', (hash,))
    if rows:
        raise CollisionException(
'''We found a collision with {0} for {1}.
Most likely the Splunk alert with configured incorrectly.
However, if this is a geniune collision, then you have a paper to write. Good luck.
'''.format(rows, hash))

    # Insert that into the database as a new alert
    create_new_alert(search_name, username, description, reason, url, hash)

class CollisionException(Exception):
    pass

def send_bot_alerts(payload):
    '''
    Creates alerts for securitybot using data provided by Splunk.

    Args:
        payload (Dict[str, str]): A dictionary of parameters provided by Splunk.
    '''
    # Generic things
    results_file = payload['results_file']
    alert_name = payload['search_name']
    splunk_url = payload['results_link']

    # Action specific things
    title = payload['configuration']['title']

    try:
        with gzip.open(results_file, 'rb') as alert_file:
            reader = csv.DictReader(alert_file)
            for row in reader:
                # TODO: eventually group by username and concat event_info
                create_securitybot_task(alert_name,
                                        row['hash'],
                                        row['ldap'],
                                        title,
                                        row['event_info'],
                                        splunk_url
                )

    except Exception:
        # Can't fix anything, so just re-raise and move on
        raise

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    try:
        # Parse stdin from Splunk
        payload = json.loads(sys.stdin.read())
        logging.info('Sending bot alert: {0}'.format(payload['search_name']))

        # initialize SQL
        init_sql()

        send_bot_alerts(payload)

        logging.info('Alert {} fired successfully.\n'.format(payload['search_name']))
    except Exception as e:
        logging.error('Failure: {}'.format(e))
    logging.info('Exiting')

if __name__ == '__main__':
    main()
