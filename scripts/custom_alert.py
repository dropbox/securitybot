#!/usr/bin/python
'''
Creates a custom Securitybot alert for a specified user.
'''
import argparse
from securitybot.sql import SQLEngine
from securitybot.util import create_new_alert

from typing import Any

def main(args):
    # type: (Any) -> None
    SQLEngine('localhost', 'root', '', 'securitybot')

    create_new_alert('custom_alert', args.name[0], args.title[0], args.reason[0])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send a custom Securitybot alert')

    parser.add_argument('-n', '--name', dest='name', nargs=1, required=True,
                        help='Username to send alert to')
    parser.add_argument('-t', '--title', dest='title', nargs=1, required=True,
                        help='User-visible alert title')
    parser.add_argument('-r', '--reason', dest='reason', nargs=1,
                        help='Long-form reason for the alert to provided context to user.')

    args = parser.parse_args()
    main(args)
