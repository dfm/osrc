# -*- coding: utf-8 -*-

import flask
from .stats import user_stats, repo_stats

__all__ = ["frontend"]

frontend = flask.Blueprint("frontend", __name__)


@frontend.route("/<username>", strict_slashes=False)
def user(username):
    stats = user_stats(username)
    if stats is None:
        return flask.abort(404)
    return flask.render_template("user.html", stats=stats)


@frontend.route("/<username>/<reponame>", strict_slashes=False)
def repo(username=None, reponame=None):
    stats = repo_stats(username, reponame)
    if stats is None:
        return flask.abort(404)
    return flask.render_template("repo.html", stats=stats)
