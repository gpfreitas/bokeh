''' Provides a Server which instantiates Application instances as clients connect

'''
from __future__ import absolute_import, print_function

import logging
log = logging.getLogger(__name__)

import sys

from tornado.httpserver import HTTPServer

from .tornado import BokehTornado

from bokeh.application import Application

from bokeh.resources import DEFAULT_SERVER_PORT

class Server(object):
    ''' A Server which creates a new Session for each connection, using an Application to initialize each Session.

    Args:
        applications (dict of str: bokeh.application.Application) or bokeh.application.Application:
            mapping from URL paths to Application instances, or a single Application to put at the root URL
            The Application is a factory for Document, with a new Document initialized for each Session.
            Each application should be identified by a path meant to go in a URL, like "/" or "/foo"
    '''

    def __init__(self, applications, **kwargs):
        if isinstance(applications, Application):
            self._applications = { '/' : applications }
        else:
            self._applications = applications
        io_loop = None
        if 'io_loop' in kwargs:
            io_loop = kwargs['io_loop']
        self._tornado = BokehTornado(self._applications, io_loop=io_loop)
        self._http = HTTPServer(self._tornado)
        self._port = DEFAULT_SERVER_PORT
        if 'port' in kwargs:
            self._port = kwargs['port']
        # these queue a callback on the ioloop rather than
        # doing the operation immediately (I think - havocp)
        try:
            self._http.bind(self._port)
            self._http.start(1)
        except OSError:
            log.critical("Cannot start bokeh server, port %s already in use" % self._port)
            sys.exit(1)

    # TODO this is broken, it's only used by test_client_server.py so fix that then remove this
    @property
    def ws_url(self):
        return "ws://localhost:" + str(self._port) + "/ws"

    @property
    def port(self):
        return self._port

    @property
    def io_loop(self):
        return self._tornado.io_loop

    def start(self):
        ''' Start the Bokeh Server's IO loop.

        Returns:
            None

        Notes:
            Keyboard interrupts or sigterm will cause the server to shut down.

        '''
        self._tornado.start()

    def stop(self):
        ''' Stop the Bokeh Server's IO loop.

        Returns:
            None

        '''
        self._tornado.stop()

    def unlisten(self):
        '''Stop listening on ports (Server will no longer be usable after calling this)

        Returns:
            None
        '''
        self._http.stop()

    def get_session(self, app_path, session_id):
        '''Gets a session by name (session must already exist)'''

        return self._tornado.get_session(app_path, session_id)

