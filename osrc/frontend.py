# -*- coding: utf-8 -*-

import flask
import string
import random
import requests
from sqlalchemy import func
from urllib.parse import urlencode

from .models import db, User
from .utils import load_json_resource
from .stats import user_stats, repo_stats

__all__ = ["frontend"]

frontend = flask.Blueprint("frontend", __name__)


@frontend.route("/<username>", strict_slashes=False)
def user(username):
    stats = user_stats(username)
    if stats is None:
        return flask.abort(404)
    if stats is False:
        return flask.render_template(
            "optedout.html",
            username=username,
        )

    event_verbs = load_json_resource("event_verbs.json")
    event_actions = load_json_resource("event_actions.json")
    return flask.render_template(
        "user.html",
        stats=stats,
        event_verbs=event_verbs,
        event_actions=event_actions,
        enumerate=enumerate,
    )


@frontend.route("/<username>/<reponame>", strict_slashes=False)
def repo(username=None, reponame=None):
    stats = repo_stats(username, reponame)
    if stats is None:
        return flask.abort(404)
    if stats is False:
        return flask.render_template(
            "optedout.html",
            username=username,
        )
    event_verbs = load_json_resource("event_verbs.json")
    return flask.render_template(
        "repo.html",
        stats=stats,
        event_verbs=event_verbs,
        enumerate=enumerate,
    )


@frontend.route("/optout/<username>", strict_slashes=False)
def optout(username=None):
    return flask.render_template("optout.html", username=username)


@frontend.route("/optout/login/<username>", strict_slashes=False)
def optout_login(username):
    state = "".join([random.choice(string.ascii_uppercase + string.digits)
                     for x in range(24)])
    flask.session["state"] = state
    flask.session["optout_username"] = username
    params = dict(
        client_id=flask.current_app.config["GITHUB_ID"],
        redirect_uri=flask.url_for(".optout_callback", username=username,
                                   _external=True),
        state=state,
    )
    return flask.redirect("https://github.com/login/oauth/authorize?{0}"
                          .format(urlencode(params)))


@frontend.route("/optout/callback", strict_slashes=False)
@frontend.route("/optout/callback/<username>", strict_slashes=False)
def optout_callback(username=None):
    if username is None:
        username = flask.session.get("optout_username")
    if username is None:
        flask.flash("Invalid username")
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))

    state1 = flask.session.get("state")
    state2 = flask.request.args.get("state")
    code = flask.request.args.get("code")
    if state1 is None or state2 is None or code is None or state1 != state2:
        flask.flash("Couldn't authorize access.")
        return flask.redirect(flask.url_for(".optout_error",
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
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))
    data = r.json()
    access = data.get("access_token", None)
    if access is None:
        flask.flash("No access token returned.")
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))

    # Check the username.
    r = requests.get("https://api.github.com/user",
                     params={"access_token": access})
    if r.status_code != requests.codes.ok:
        flask.flash("Couldn't get user information.")
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))
    data = r.json()
    login = data.get("login", None)
    if login is None or login.lower() != username.lower():
        flask.flash("You have to log in as '{0}' in order to opt-out."
                    .format(username))
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))

    # Save the opt-out to the database.
    user = User.query.filter(
        func.lower(User.login) == func.lower(username)).first()
    if user is None:
        flask.flash("Unknown user: '{0}'.".format(username))
        return flask.redirect(flask.url_for(".optout_error",
                                            username=username))
    user.active = False
    db.session.add(user)
    db.session.commit()

    return flask.redirect(flask.url_for(".optout_success", username=username))


@frontend.route("/optout/error", strict_slashes=False)
@frontend.route("/optout/error/<username>", strict_slashes=False)
def optout_error(username=None):
    return flask.render_template("optout-error.html", username=username)


@frontend.route("/optout/success", strict_slashes=False)
@frontend.route("/optout/success/<username>", strict_slashes=False)
def optout_success(username=None):
    return flask.render_template("optout-success.html")
