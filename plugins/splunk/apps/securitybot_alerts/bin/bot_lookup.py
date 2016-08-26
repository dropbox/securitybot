#!/usr/local/env python
'''
Performs a MySQL query to return any events that have a SHA-256 hash matching
an event handled by the bot.
'''
__author__ = 'Alex Bertsch'
__email__ = 'abertsch@dropbox.com'

import sys
import csv
import logging

from securitybot.sql import SQLEngine, init_sql

from typing import Any, Sequence

def find_on_hash(hash):
    # type: (str) -> Sequence[Any]
    match = SQLEngine.execute('SELECT comment, performed, authenticated FROM user_responses WHERE hash=UNHEX(%s)', (hash,))
    if len(match) != 1:
        # This catches collisions too, which is probably (hopefully) overkill
        return None
    item = match[0]
    return item[0], bool(item[1]), bool(item[2])

def main():
    # type: () -> None
    if len(sys.argv) != 5:
        print 'Usage: python bot_lookup.py [hash] [comment] [performed] [authenticated]'

    # Initialize SQL
    init_sql()

    hash_field = sys.argv[1]
    comment_field = sys.argv[2]
    performed_field = sys.argv[3]
    authenticated_field = sys.argv[4]

    infile = sys.stdin
    outfile = sys.stdout

    # Load in query from stdin
    inbound = csv.DictReader(infile)

    # Prep return CSV with the same format
    header = inbound.fieldnames
    outbound = csv.DictWriter(outfile, fieldnames=header)
    outbound.writeheader()

    for entry in inbound:
        hash = entry[hash_field]

        try:
            res = find_on_hash(hash)
            if res is not None:
                comment, performed, authenticated = res

                entry[comment_field] = comment
                entry[performed_field] = performed
                entry[authenticated_field] = authenticated
        except Exception as e:
            logging.warn('An exception was encountered making a DB call: {0}'.format(e))

        outbound.writerow(entry)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
