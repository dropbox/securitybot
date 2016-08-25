'''
A simple script to allow querying the securitybot DB and
viewing recent alerts, mostly for debugging purposes.
'''
import argparse
import re

from securitybot.sql import SQLEngine

from typing import Any, Dict, List, Sequence

BLACKLIST_QUERY = '''
SELECT ldap
FROM blacklist
'''

IGNORED_QUERY = '''
SELECT ldap, title, reason, until
FROM ignored
'''

IGNORED_FIELDS = ['ldap', 'title', 'reason', 'until']

MAIN_QUERY = '''
SELECT HEX(alerts.hash),
       title,
       ldap,
       reason,
       description,
       splunk_url,
       comment,
       performed,
       authenticated,
       status,
       event_time
FROM alerts
JOIN user_responses ON alerts.hash = user_responses.hash
JOIN alert_status ON alerts.hash = alert_status.hash
'''

QUERY_FIELDS = ['hash',
                'title',
                'ldap',
                'reason',
                'description',
                'splunk_url',
                'comment',
                'performed',
                'authenticated',
                'status',
                'event_time']

STATUS_WHERE = 'status = %s'

PERFORMED_WHERE = 'performed = %s'

TITLE_WHERE = 'title IN ({0})'

ORDER_BY = 'ORDER BY {0}' # wow

BEFORE = 'event_time <= DATE_ADD(NOW(), INTERVAL %s HOUR)'

AFTER = 'event_time >= DATE_ADD(NOW(), INTERVAL %s HOUR)'

HAS_WHERE = False

def build_in(num_titles):
    # type: (int) -> str
    return TITLE_WHERE.format(','.join(['%s' for _ in range(num_titles)]))

LIMIT = 'LIMIT %s'

def init():
    # type: () -> None
    SQLEngine('localhost', 'root', '', 'securitybot')

def main(args):
    # type: (Any) -> None
    if args.blacklist:
        fields, matrix = blacklist(args)
    elif args.ignored:
        fields, matrix = ignored(args)
    else:
        fields, matrix = alerts(args)

    pretty_print(fields, matrix)

def blacklist(args):
    # type: (Any) -> Sequence[Any]
    fields = ['ldap']
    results = SQLEngine.execute(BLACKLIST_QUERY)
    return fields, [list(row) for row in results]

def ignored(alerts):
    # type: (Any) -> Sequence[Any]
    results = SQLEngine.execute(IGNORED_QUERY)
    return IGNORED_FIELDS, [list(row) for row in results]

def alerts(args):
    # type: (Any) -> Sequence[Any]
    params = []  # type: List[Any]
    query = MAIN_QUERY

    # Prepare for possible limited status
    if args.status is not None:
        query += build_where(STATUS_WHERE)
        params += args.status

    # Prepare for possible limited performed boolean
    if args.performed is not None:
        query += build_where(PERFORMED_WHERE)
        params += args.performed

    # Prepare for possible title restrictions
    if args.titles is not None:
        query += build_where(build_in(len(args.titles)))
        params.extend(args.titles)

    # Add time bounding
    if args.before is not None:
        query += build_where(BEFORE)
        params += [parse_time(args.before[0])]
    if args.after is not None:
        query += build_where(AFTER)
        params += [parse_time(args.after[0])]

    # Append limit restriction and order by
    query += build_order_by(args.order[0]) + '\n'
    query += LIMIT
    params += args.limit

    # Perform query
    raw_results = SQLEngine.execute(query, params)
    results = build_query_dict(raw_results)

    to_remove = [] # type: List[str]

    # Set extra fields to remove
    if args.drop is not None:
        to_remove.extend(args.drop)

    # Remove hashes if not specified
    if not args.hash:
        to_remove.append('hash')

    # Remove status if one was specified earlier
    if args.status is not None:
        to_remove.append('status')

    # Remove time if not specified
    if not args.time:
        to_remove.append('event_time')

    # Remove URL if not specified
    if not args.url:
        to_remove.append('splunk_url')

    # Anonymize if specified
    if args.anon:
        to_remove.append('ldap')

    # Remove columns
    for row in results:
        for col in to_remove:
            row.pop(col, None)

    # Grab list of fields and convert to list of lists
    fields = [field for field in QUERY_FIELDS if field not in to_remove]
    matrix = [[row[field] for field in fields] for row in results]

    return fields, matrix

def build_where(condition):
    # type: (str) -> str
    '''
    Builds another part of a where clause depending on whether any other clauses
    have been used yet. Inspects global HAS_WHERE and adds either a WHERE or AND.
    '''
    global HAS_WHERE
    s = ''
    if HAS_WHERE:
        s += 'AND'
    else:
        HAS_WHERE = True
        s += 'WHERE'
    return '{0} {1}\n'.format(s, condition)

def build_order_by(order):
    # type (str) -> str
    if order in ['event_time', 'ldap', 'title']:
        formatted = ORDER_BY.format(order)
        if order == 'event_time':
            formatted += ' DESC'
        return formatted
    raise ValueError('{0} is an invalid column to order on.'.format(order))

TIME_REGEX = re.compile(r'(-?[0-9]+)h', flags=re.IGNORECASE)

def parse_time(time):
    # type: (str) -> int
    '''
    Parses a -Xh string to an int.
    Within the code, the fact that it's negative is actually optional, but I'd rather
    not directly expose that fact.
    '''
    m = TIME_REGEX.match(time)
    if m is None:
        raise ValueError('{0} is an invalid time.'.format(time))
    return int(m.group(1))

def build_query_dict(results):
    # type: (Sequence[Sequence[Any]]) -> List[Dict[str, Any]]
    '''Builds a list of dictionaries from the results of a query.'''
    return [{field: value for field, value in zip(QUERY_FIELDS, row)} for row in results]

def pretty_print(fields, matrix):
    # type: (List[str], List[List[Any]]) -> None
    '''Pretty prints a matrix of data.'''
    contents = [fields] + matrix
    contents = [[str(i) for i in row] for row in contents]
    # Pretty print rows
    # Find maximum length for each column in the context matrix
    lens = [max([len(item) for item in col]) for col in zip(*contents)]
    # Prepare formatting string for column sizes
    fmt = ' | '.join('{{:{}}}'.format(x) for x in lens)
    # Apply formatting to each row in the context string
    table = [fmt.format(*row) for row in contents]
    # Add header separator
    table.insert(1, '-' * len(table[0]))
    # Join lines with newline
    result = '\n'.join(table)

    print result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Explore the Securitybot DB')

    # Which table to query on -- defaults to alerts
    parser.add_argument('--blacklist', dest='blacklist', action='store_true',
                        help='Rather than query alerts, displays the blacklist.')

    parser.add_argument('--ignored', dest='ignored', action='store_true',
                        help='Rather than query alerts, displays currently ignored alerts.')

    # Alert arguments
    parser.add_argument('--titles', dest='titles', type=str, nargs='+',
                        help='One or more titles of alerts to grab.')

    parser.add_argument('-o', '--order', dest='order', type=str, default=['event_time'], nargs=1,
                        help='Name of column to order by. Must be one of event_time, ldap, title. '+
                             'Defaults to event_time.')

    parser.add_argument('-s', '--status', dest='status', type=int, nargs=1,
                        help='The status of the alerts to return. ' +
                             '0 is new, 1 is in progress, 2 is closed.')

    parser.add_argument('-p', '--performed', dest='performed', type=int, nargs=1,
                        help='0 to select alerts that the user did not perform, 1 otherwise.')

    parser.add_argument('-l', '--limit', dest='limit', type=int, default=[25], nargs=1,
                        help='The maximum number of results to return. Defaults to 25.')

    parser.add_argument('--hash', dest='hash', action='store_true',
                        help='If present, will display hash of alert.')

    parser.add_argument('-t', '--time', dest='time', action='store_true',
                        help='If present, will output time at which alert was first logged.')

    parser.add_argument('-u', '--url', dest='url', action='store_true',
                        help='If present, will output Splunk URL of alert\'s saved search.')

    parser.add_argument('-a', '--anon', dest='anon', action='store_true',
                        help='If present, will anonymize output.')

    parser.add_argument('--drop', dest='drop', type=str, nargs='+',
                        help='One or more extra fields to drop.')

    # Time bounding
    parser.add_argument('--after', dest='after', type=str, nargs=1,
                        help='Time range all alerts must be after in negative hours, e.g. -6h. ' +
                             'Note: you may have to use --after=-6h.')
    parser.add_argument('--before', dest='before', type=str, nargs=1,
                        help='Time range all alerts must be before in negative hours, e.g. -2h. ' +
                             'Note: you may have to use --before=-2h.')

    args = parser.parse_args()

    init()
    main(args)
