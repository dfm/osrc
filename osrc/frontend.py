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
    # Get the user information.
    user_info = stats.get_user_info(username)

    # Get the usage stats and bail if there isn't enough information.
    usage = stats.get_usage_stats(username)
    if usage is None:
        return flask.jsonify(message="Not enough information for {0}."
                             .format(username)), 404

    return flask.jsonify(dict(user_info, usage=usage))
