#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["app"]

import json
import flask
import redis
import logging
import requests


app = flask.Flask(__name__)
app.config.from_object("ghdata.config")

ghapi_url = "https://api.github.com"

fh = logging.FileHandler(app.config["LOG_FILENAME"])
fh.setLevel(logging.WARNING)
fh.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s "
    "[in %(pathname)s:%(lineno)d]"
))
app.logger.addHandler(fh)


@app.before_request
def before_request():
    flask.g.redis = redis.Redis()
    flask.g.ghauth = {"client_id": app.config["GITHUB_ID"],
                      "client_secret": app.config["GITHUB_SECRET"]}


@app.route("/")
def index():
    return "GH Report Card"


@app.route("/<ghuser>")
def user(ghuser):
    # Start by getting the user information from the API.
    r = requests.get(ghapi_url + "/users/" + ghuser, params=flask.g.ghauth)
    if r.status_code != requests.codes.ok:
        logging.error("GitHub API failed: {0}".format(r.status_code))
        logging.error(r.text)
        flask.abort(404)

    # Parse the JSON response.
    data = r.json()

    # Get the user's name or login.
    name = data.get("name") or data.get("login") or ghuser

    # Get the user histogram.
    data = flask.g.redis.hgetall("gh:user:{0}:day".format(ghuser))
    hist = [0] * 7
    for k, v in data.iteritems():
        hist[int(k)] = int(v)

    return json.dumps({"name": name, "hist": hist})
