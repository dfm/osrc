# -*- coding: utf-8 -*-

import flask
from functools import wraps

from .stats import user_stats, repo_stats

__all__ = ["api"]

api = flask.Blueprint("api", __name__)


# JSONP support.
# Based on: https://gist.github.com/aisipos/1094140
def jsonp(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = flask.request.args.get("callback", False)
        if callback:
            r = f(*args, **kwargs)
            content = "{0}({1})".format(callback, r.data.decode("utf-8"))
            mime = "application/javascript"
            resp = flask.current_app.response_class(content, mimetype=mime,
                                                    status=r.status_code)
        else:
            resp = f(*args, **kwargs)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    return decorated_function


@api.errorhandler(404)
def error_handler_404(e):
    resp = flask.jsonify(message="Not found")
    resp.status_code = 404
    return resp


@api.errorhandler(403)
def error_handler_403(e):
    resp = flask.jsonify(message="This user has opted out of the OSRC")
    resp.status_code = 403
    return resp


@api.route("/<username>", strict_slashes=False)
@jsonp
def user(username=None):
    stats = user_stats(username)
    if stats is None:
        return flask.abort(404)
    if stats is False:
        return flask.abort(403)
    return flask.jsonify(stats)


@api.route("/<username>/<reponame>", strict_slashes=False)
@jsonp
def repo(username=None, reponame=None):
    stats = repo_stats(username, reponame)
    if stats is None:
        return flask.abort(404)
    return flask.jsonify(stats)
