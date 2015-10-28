#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse

from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer

try:
    import osrc  # NOQA
except ImportError:
    import sys
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
finally:
    from osrc import create_app

if __name__ == "__main__":
    dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_settings = os.path.join(dirname, "local.py")

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=3031, type=int,
                        help="the port to expose")
    parser.add_argument("-f", "--filename",
                        default=None,
                        help="a Python file with the app settings")
    args = parser.parse_args()

    # Build the Flask app.
    app = create_app(args.filename)

    # Fire up the tornado server.
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(args.port)
    IOLoop.instance().start()
