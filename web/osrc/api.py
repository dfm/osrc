# -*- coding: utf-8 -*-

__all__ = ["api"]

import flask
from functools import wraps

from .stats import user_stats, repo_stats

api = flask.Blueprint("api", __name__)


# JSONP support.
# Based on: https://gist.github.com/aisipos/1094140
def jsonp(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = flask.request.args.get("callback", False)
        if callback:
            r = f(*args, **kwargs)
            content = "{0}({1})".format(callback, r.data)
            mime = "application/javascript"
            return flask.current_app.response_class(content, mimetype=mime,
                                                    status=r.status_code)
        else:
            return f(*args, **kwargs)
    return decorated_function


@api.errorhandler(404)
def error_handler(e):
    resp = flask.jsonify(message="Not Found")
    resp.status_code = 404
    return resp


@api.route("/<username>.json")
@jsonp
def user(username):
    stats = user_stats(username)
    if stats is None:
        return flask.abort(404)
    return flask.jsonify(stats)


@api.route("/<username>/<reponame>.json")
@jsonp
def repo(username, reponame):
    stats = repo_stats(username, reponame)
    if stats is None:
        return flask.abort(404)
    return flask.jsonify(stats)
