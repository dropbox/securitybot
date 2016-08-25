'''
API for the Securitybot database.
'''
# Securitybot imports
from securitybot.sql import SQLEngine, SQLEngineException, init_sql
from securitybot.util import create_new_alert

# Typing
from typing import Any, Dict, List, Sequence

def init_api():
    # type: () -> None
    init_sql()

# API functions
'''
Every API call returns a JSON response through the web endpoints.
These functions themselves return dictionaries.
The generic dictionary format is as follows:
{
    "ok": [True, False]  # Whether or not the API call was successful
    "error": str         # Error from the API endpoint
    "info": str          # Additional information about the API call
    "content": Dict      # Full results from the API call.
}
The value of "content" varies on the API call.
'''

def build_response():
    # type: () -> Dict[str, Any]
    '''Builds an empty response dictionary.'''
    return {
        'ok': False,
        'error': '',
        'info': '',
        'content': {}
    }

def exception_response(e):
    res = build_response()
    res['error'] = str(e)
    return res

def build_arguments(default, args, response):
    # type: (Dict[str, Any], Dict[str, Any], Dict[str, Any]) -> None
    # Add all default arguments to args
    for arg in default:
        if arg not in args:
            args[arg] = default[arg]

    # Warn about additional arguments
    for arg in args:
        if arg not in default:
            response['info'] += 'WARNING: unknown argument {}\n'.format(arg)

def build_in(clause, num_titles):
    # type: (str, int) -> str
    return clause.format(','.join(['%s' for _ in range(num_titles)]))

def build_where(condition, has_where):
    # type: (str, bool) -> str
    '''
    Builds another part of a where clause depending on whether any other clauses
    have been used yet.
    '''
    s = 'AND' if has_where else 'WHERE'
    return '{0} {1}\n'.format(s, condition)

def build_query_dict(fields, results):
    # type: (List[str], Sequence[Sequence[Any]]) -> List[Dict[str, Any]]
    '''Builds a list of dictionaries from the results of a query.'''
    return [{field: value for field, value in zip(fields, row)} for row in results]

# Querying alerts

ALERTS_QUERY = '''
SELECT HEX(alerts.hash),
       title,
       ldap,
       reason,
       description,
       url,
       comment,
       performed,
       authenticated,
       status,
       event_time
FROM alerts
JOIN user_responses ON alerts.hash = user_responses.hash
JOIN alert_status ON alerts.hash = alert_status.hash
'''

ALERTS_FIELDS = ['hash',
                'title',
                'ldap',
                'reason',
                'description',
                'url',
                'comment',
                'performed',
                'authenticated',
                'status',
                'event_time']



STATUS_WHERE = 'status = %s'
PERFORMED_WHERE = 'performed = %s'
TITLE_IN = 'title IN ({0})'
LDAP_IN = 'ldap IN ({0})'
BEFORE = 'event_time <= FROM_UNIXTIME(%s)'
AFTER = 'event_time >= FROM_UNIXTIME(%s)'
LIMIT = 'LIMIT %s'

DEFAULT_QUERY_ARGUMENTS = {
    'limit': 50,  # max number of alerts to return
    'titles': None,  # titles of alerts to return
    'ldap': None,  # usernames of alerts to return
    'status': None,  # status of alerts to return
    'performed': None,  # performed status of alerts to return
    'authenticated': None,  # authenticated status of alerts to return
    'after': None,  # starting time of alerts to return, as a unix timestamp
    'before': None,  # ending time of alerts to return, as a unix timestamp
}

def query(**kwargs):
    # type: (**Any) -> Dict[str, Any]
    '''
    Queries the alerts database.

    Args:
        **kwargs: Arguments to the API endpoint.
    Content:
        {
            "alerts": List[Dict]: list of dictionaries representing alerts in the database
        }
        Each alert has all of the fields in QUERY_FIELDS.
    '''
    response = build_response()
    args = kwargs
    build_arguments(DEFAULT_QUERY_ARGUMENTS, args, response)

    # Build query
    query = ALERTS_QUERY
    params = [] # type: List[Any]
    has_where = False

    # Add possible where statements
    if args['status'] is not None:
        query += build_where(STATUS_WHERE, has_where)
        params.append(args['status'])
        has_where = True

    if args['performed'] is not None:
        query += build_where(PERFORMED_WHERE, has_where)
        params.append(args['performed'])
        has_where = True

    if args['titles'] is not None:
        query += build_where(build_in(TITLE_IN, len(args['titles'])), has_where)
        params.extend(args['titles'])
        has_where = True

    if args['ldap'] is not None:
        query += build_where(build_in(LDAP_IN, len(args['ldap'])), has_where)
        params.extend(args['ldap'])
        has_where = True

    # Add time bounds
    if args['before'] is not None:
        query += build_where(BEFORE, has_where)
        params.append(args['before'])
        has_where = True
    if args['after'] is not None:
        query += build_where(AFTER, has_where)
        params.append(args['after'])
        has_where = True

    # Add limit
    query += 'ORDER BY event_time DESC\n'
    query += LIMIT
    params.append(args['limit'])

    # Make SQL query
    try:
        raw_results = SQLEngine.execute(query, params)
    except SQLEngineException:
        response['error'] = 'Invalid parameters'
        return response

    results = build_query_dict(ALERTS_FIELDS, raw_results)

    # Convert datetimes to unix time
    for alert in results:
        alert['event_time'] = int(alert['event_time'].strftime('%s'))

    response['content']['alerts'] = results
    response['ok'] = True
    return response

# Querying ignored

IGNORED_QUERY = '''
SELECT ldap, title, reason, until
FROM ignored
'''

IGNORED_ORDER_BY = 'ORDER BY until DESC\n'

IGNORED_FIELDS = ['ldap', 'title', 'reason', 'until']

DEFAULT_IGNORED_ARGUMENTS = {
    'limit': 50,
    'ldap': None,
}

def ignored(**kwargs):
    # type: (**Any) -> Dict[str, Any]
    '''
    Makes a call to the ignored database.
    Content:
        {
            "ignored": List[Dict]: list of dictionaries representing ignored alerts
        }
        Each item in "ignored" has fields in IGNORED_FIELDS
    '''
    response = build_response()
    args = kwargs
    build_arguments(DEFAULT_IGNORED_ARGUMENTS, args, response)

    query = IGNORED_QUERY
    params = [] # type: List[Any]

    if args['ldap'] is not None:
        query += build_where(build_in(LDAP_IN, len(args['ldap'])), False)
        params.extend(args['ldap'])

    query += IGNORED_ORDER_BY
    query += LIMIT
    params.append(args['limit'])

    try:
        raw_results = SQLEngine.execute(query, params)
    except SQLEngineException:
        response['error'] = 'Invalid parameters'
        return response

    results = build_query_dict(IGNORED_FIELDS, raw_results)

    # Convert datetimes to timestamps
    for ignored in results:
        ignored['until'] = int(ignored['until'].strftime('%s'))

    response['content']['ignored'] = results
    response['ok'] = True
    return response

# Querying blacklist

BLACKLIST_QUERY = '''
SELECT ldap
FROM blacklist
ORDER BY ldap
LIMIT %s
'''

BLACKLIST_FIELDS = ['ldap']

DEFAULT_BLACKLIST_ARGUMENTS = {
    'limit': 50,
}

def blacklist(**kwargs):
    # type: (**Any) -> Dict[str, Any]
    '''
    Makes a call to the ignored database.
    Content:
        {
            "blacklist": List[Dict]: list of dictionaries representing ignored alerts
        }
        Each item in "blacklist" has only an ldap
    '''
    response = build_response()
    args = kwargs
    build_arguments(DEFAULT_BLACKLIST_ARGUMENTS, args, response)
    try:
        raw_results = SQLEngine.execute(BLACKLIST_QUERY, (args['limit'],))
    except SQLEngineException:
        response['error'] = 'Invalid parameters'
        return response

    results = build_query_dict(BLACKLIST_FIELDS, raw_results)

    response['content']['blacklist'] = results
    response['ok'] = True
    return response

# Custom alert creation
def create_alert(ldap, title, description, reason):
    # type: (str, str, str, str) -> Dict[str, Any]
    '''
    Creates a new alert.
    Args:
        ldap: The username of the person to send an alert to
        title: The internal title
        description: A short slug that describes the alert/user visible title
        reason: The reason for creating the alert
    Content:
        Empty.
    '''
    response = build_response()
    try:
        create_new_alert(title, ldap, description, reason)
    except SQLEngineException:
        response['error'] = 'Invalid parameters'
        return response
    response['ok'] = True
    return response
