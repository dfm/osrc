#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["app"]

import flask
import requests
import redis


app = flask.Flask(__name__)
app.config.from_object("ghdata.config")


@app.before_request
def before_request():
    flask.g.redis = redis.Redis()


@app.route("/")
def index():
    return "GH Report Card"


@app.route("/<ghuser>")
def user(ghuser):
    pass
