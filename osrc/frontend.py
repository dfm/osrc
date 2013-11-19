#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import json
import flask
import urllib
import string
import random
import requests
from math import sqrt

from . import stats
from .database import get_connection, format_key

frontend = flask.Blueprint("frontend", __name__)


# Custom Jinja2 filters.
def firstname(value):
    return value.split()[0]


def compare(user1, user2):
    return stats.get_comparison(user1, user2)


@frontend.route("/")
def index():
    return flask.render_template("index.html")


def get_user_stats(username):
    # Get the user information.
    user_info = stats.get_user_info(username)
    if user_info is None:
        return None

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
    stats = get_user_stats(username)
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

    # Load the list of event verbs.
    with flask.current_app.open_resource("event_verbs.json") as f:
        event_verbs = json.load(f)

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
                                 event_verbs=event_verbs,
                                 week_type=week_type,
                                 best_time=best_time,
                                 enumerate=enumerate,
                                 **stats)


@frontend.route("/<username>.json")
def stats_view(username):
    stats = get_user_stats(username)
    if stats is None:
        return flask.jsonify(message="Not enough information for {0}."
                             .format(username)), 404
    return flask.jsonify(stats)


@frontend.route("/<username>/<reponame>")
def repo_view(username, reponame):
    s = stats.get_repo_info(username, reponame)
    if s is None:
        return flask.render_template("noinfo.html")
    return flask.render_template("repo.html", **s)


@frontend.route("/<username>/<reponame>.json")
def repo_stats_view(username, reponame):
    s = stats.get_repo_info(username, reponame)
    if s is None:
        return flask.jsonify(message="Not enough information for {0}/{1}."
                             .format(username, reponame)), 404
    return flask.jsonify(**s)


@frontend.route("/opt-out/<username>")
def opt_out(username):
    return flask.render_template("opt-out.html", username=username)


@frontend.route("/opt-out/<username>/login")
def opt_out_login(username):
    state = "".join([random.choice(string.ascii_uppercase + string.digits)
                     for x in range(24)])
    flask.session["state"] = state
    params = dict(
        client_id=flask.current_app.config["GITHUB_ID"],
        redirect_uri=flask.url_for(".opt_out_callback", username=username,
                                   _external=True),
        state=state,
    )
    return flask.redirect("https://github.com/login/oauth/authorize?{0}"
                          .format(urllib.urlencode(params)))


@frontend.route("/opt-out/<username>/callback")
def opt_out_callback(username):
    state1 = flask.session.get("state")
    state2 = flask.request.args.get("state")
    code = flask.request.args.get("code")
    if state1 is None or state2 is None or code is None or state1 != state2:
        flask.flash("Couldn't authorize access.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Get an access token.
    params = dict(
        client_id=flask.current_app.config["GITHUB_ID"],
        client_secret=flask.current_app.config["GITHUB_SECRET"],
        code=code,
    )
    r = requests.post("https://github.com/login/oauth/access_token",
                      data=params, headers={"Accept": "application/json"})
    if r.status_code != requests.codes.ok:
        flask.flash("Couldn't acquire an access token from GitHub.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))
    data = r.json()
    access = data.get("access_token", None)
    if access is None:
        flask.flash("No access token returned.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Check the username.
    r = requests.get("https://api.github.com/user",
                     params={"access_token": access})
    if r.status_code != requests.codes.ok:
        flask.flash("Couldn't get user information.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))
    data = r.json()
    login = data.get("login", None)
    if login is None or login.lower() != username.lower():
        flask.flash("You have to log in as '{0}' in order to opt-out."
                    .format(username))
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Save the opt-out to the database.
    user = username.lower()
    get_connection().set(format_key("user:{0}:optout".format(user)), True)

    return flask.redirect(flask.url_for(".opt_out_success", username=username))


@frontend.route("/opt-out/<username>/error")
def opt_out_error(username):
    return flask.render_template("opt-out-error.html", username=username)


@frontend.route("/opt-out/<username>/success")
def opt_out_success(username):
    return flask.render_template("opt-out-success.html")
