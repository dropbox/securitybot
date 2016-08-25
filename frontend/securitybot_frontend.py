#!/usr/bin/env python
'''
Front-end for the Securitybot database.
'''
# Python includes
import argparse
from csv import reader
import logging
import os

# Tornado includes
import tornado.httpserver
import tornado.ioloop
import tornado.netutil
import tornado.web

# Securitybot includes
import securitybot_api as api

# Typing
from typing import Sequence

def get_endpoint(handler, defaults, callback):
    '''
    Makes a call to an API endpoint, using parameters from default.
    '''
    try:
        args = {}
        for name, default, parser in defaults:
            arg = handler.get_argument(name, default=None)
            if arg is None:
                args[name] = default
            else:
                args[name] = parser(arg)
        handler.write(callback(**args))
    except Exception as e:
        handler.write(api.exception_response(e))

# List of tuples of name, default, parser
QUERY_ARGUMENTS = [
    ('limit', 50, int),
    ('titles', None, lambda s: list(reader([s]))[0]),
    ('ldap', None, lambda s: list(reader([s]))[0]),
    ('status', None, int),
    ('performed', None, int),
    ('authenticated', None, int),
    ('after', None, int),
    ('before', None, int),
]

class QueryHandler(tornado.web.RequestHandler):
    def get(self):
        get_endpoint(self, QUERY_ARGUMENTS, api.query)

IGNORED_ARGUMENTS = [
    ('limit', 50, int),
    ('ldap', None, lambda s: list(reader([s]))[0]),
]

class IgnoredHandler(tornado.web.RequestHandler):
    def get(self):
        get_endpoint(self, IGNORED_ARGUMENTS, api.ignored)

BLACKLIST_ARGUMENTS = [
    ('limit', 50, int),
]

class BlacklistHandler(tornado.web.RequestHandler):
    def get(self):
        get_endpoint(self, BLACKLIST_ARGUMENTS, api.blacklist)

class NewAlertHandler(tornado.web.RequestHandler):
    def post(self):
        response = api.build_response()
        args = {}
        for name in ['title', 'ldap', 'description', 'reason']:
            args[name] = self.get_argument(name, default=None)
            if args[name] is None:
                response['error'] += 'ERROR: {} must be specified!\n'.format(name)
        if all(v is not None for v in args.values()):
            self.write(api.create_alert(args['ldap'],
                                        args['title'],
                                        args['description'],
                                        args['reason']))
        else:
            self.write(response)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render()

    def render(self):
        self.write(self.render_string("templates/index.html"))

class SecuritybotService(object):
    '''Registers handlers and kicks off the HTTPServer and IOLoop'''

    def __init__(self, port):
        # type: (str, str, bool) -> None
        self.requests = 0
        self.port = port
        static_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
        self._app = tornado.web.Application([
            (r'/', IndexHandler),
            (r'/api/query', QueryHandler),
            (r'/api/ignored', IgnoredHandler),
            (r'/api/blacklist', BlacklistHandler),
            (r'/api/create', NewAlertHandler),
        ],
        xsrf_cookie=True,
        static_path=static_path,
        )
        self.server = tornado.httpserver.HTTPServer(self._app)
        self.sockets = tornado.netutil.bind_sockets(self.port, '0.0.0.0')
        self.server.add_sockets(self.sockets)
        for s in self.sockets:
            sockname = s.getsockname()
            logging.info('Listening on {socket}, port {port}'
                         .format(socket=sockname[0], port=sockname[1]))

    def start(self):
        # type: () -> None
        logging.info('Starting.')
        tornado.ioloop.IOLoop.instance().start()

    def stop(self):
        # type: () -> None
        logging.info('Stopping.')
        self.server.stop()

    def get_socket(self):
        # type: () -> Sequence[str]
        return self.sockets[0].getsockname()[:2]

def init():
    # type: () -> None
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s %(levelname)s] %(message)s')

    api.init_api()

def main(port):
    # type: (int) -> None
    logging.info('Starting up!')
    try:
        service = SecuritybotService(port)

        def shutdown():
            logging.info('Shutting down!')
            service.stop()
            logging.info('Stopped.')
            os._exit(0)

        service.start()
    except Exception as e:
        logging.error('Uncaught exception: {e}'.format(e=e))


if __name__ == '__main__':
    init()

    parser = argparse.ArgumentParser(description='Securitybot frontent')
    parser.add_argument('--port', dest='port', default='8888', type=int)
    args = parser.parse_args()

    main(args.port)
