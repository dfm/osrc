#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer

from werkzeug.serving import run_simple

from osrc import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=3031, type=int,
                        help="the port to expose")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="debugging interface")
    parser.add_argument("-f", "--filename",
                        default=None,
                        help="a Python file with the app settings")
    args = parser.parse_args()
    print("port: {0}".format(args.port))
    print("config: {0}".format(args.filename))

    app = create_app(args.filename)
    if args.debug:
        run_simple("0.0.0.0", args.port, app, use_reloader=True,
                   use_debugger=True)
    else:
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(args.port)
        IOLoop.instance().start()
