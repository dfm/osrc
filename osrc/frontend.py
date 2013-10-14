#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import json
import flask
from math import sqrt

from . import stats

frontend = flask.Blueprint("frontend", __name__)


# Custom Jinja2 filters.
def firstname(value):
    return value.split()[0]


def compare(user1, user2):
    return stats.get_comparison(user1, user2)


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

    # Load the list of languages.
    with flask.current_app.open_resource("languages.json") as f:
        language_list = json.load(f)

    # Load the list of event action descriptions.
    with flask.current_app.open_resource("event_actions.json") as f:
        event_actions = json.load(f)

    # Figure out the user's best time of day.
    with flask.current_app.open_resource("time_of_day.json") as f:
        times_of_day = json.load(f)
    best_time = (max(enumerate(stats["usage"]["day"]),
                     key=lambda o: o[1])[0], None)
    for tod in times_of_day:
        times = tod["times"]
        if times[0] <= best_time[0] < times[1]:
            best_time = (best_time[0], tod["name"])
            break

    # Compute the name of the best description of the user's weekly schedule.
    with flask.current_app.open_resource("week_types.json") as f:
        week_types = json.load(f)
    best_dist = -1
    week_type = None
    user_vector = stats["usage"]["week"]
    norm = 1.0 / sqrt(sum([v * v for v in user_vector]))
    user_vector = [v*norm for v in user_vector]
    for week in week_types:
        vector = week["vector"]
        norm = 1.0 / sqrt(sum([v * v for v in vector]))
        dot = sum([(v*norm-w) ** 2 for v, w in zip(vector, user_vector)])
        if best_dist < 0 or dot < best_dist:
            best_dist = dot
            week_type = week["name"]

    return flask.render_template("user.html",
                                 adjectives=adjectives,
                                 language_list=language_list,
                                 event_actions=event_actions,
                                 week_type=week_type,
                                 best_time=best_time,
                                 **stats)


@frontend.route("/<username>.json")
def stats_view(username):
    stats = get_all_the_stats(username)
    if stats is None:
        return flask.jsonify(message="Not enough information for {0}."
                             .format(username)), 404
    return flask.jsonify(stats)
