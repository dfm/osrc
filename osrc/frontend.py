#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import json
import flask

from . import stats

frontend = flask.Blueprint("frontend", __name__)


@frontend.route("/")
def index():
    return "HELLO"


def get_all_the_stats(username):
    # Get the user information.
    user_info = stats.get_user_info(username)

    # Get the usage stats and bail if there isn't enough information.
    usage = stats.get_usage_stats(username)
    if usage is None:
        return None

    # Get the social stats.
    social_stats = stats.get_social_stats(username)
    return dict(dict(user_info, **social_stats), usage=usage)


@frontend.route("/<username>")
def user_view(username):
    # Get the stats.
    stats = get_all_the_stats(username)
    if stats is None:
        return flask.render_template("noinfo.html")

    # Load the list of adjectives.
    with flask.current_app.open_resource("adjectives.json") as f:
        adjectives = json.load(f)

    return flask.render_template("user.html", adjectives=adjectives, **stats)


@frontend.route("/<username>.json")
def stats_view(username):
    stats = get_all_the_stats(username)
    if stats is None:
        return flask.jsonify(message="Not enough information for {0}."
                             .format(username)), 404
    return flask.jsonify(stats)
