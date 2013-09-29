#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import flask

from . import stats

frontend = flask.Blueprint("frontend", __name__)


@frontend.route("/")
def index():
    return "HELLO"


@frontend.route("/<username>/stats")
def stats_view(username):
    return flask.jsonify(stats.get_user_info(username))
