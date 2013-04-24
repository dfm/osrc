#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["app"]

import re
import json
import flask
import redis
import logging
import requests


app = flask.Flask(__name__)
app.config.from_object("ghdata.config")

ghapi_url = "https://api.github.com"
mqapi_url = "http://open.mapquestapi.com/geocoding/v1/address"
tzapi_url = "http://www.earthtools.org/timezone-1.1/{lat}/{lng}"
tz_re = re.compile(r"<offset>([\-0-9]+)</offset>")

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


@app.route("/<username>")
def user(username):
    ghuser = username.lower()

    # Start by getting the user information from the API.
    r = requests.get(ghapi_url + "/users/" + ghuser, params=flask.g.ghauth)
    if r.status_code != requests.codes.ok:
        logging.error("GitHub API failed: {0}".format(r.status_code))
        logging.error(r.text)
        flask.abort(404)

    # Parse the JSON response.
    user = r.json()

    # Get the user's name or login.
    name = user.get("name") or user.get("login") or username

    # Get the user histogram.
    pipe = flask.g.redis.pipeline()
    pipe.hgetall("gh:user:{0}:day".format(ghuser))
    pipe.hgetall("gh:user:{0}:hour".format(ghuser))
    pipe.zrevrange("gh:user:{0}:connection".format(ghuser), 0, 5,
                   withscores=True)
    pipe.zrevrange("gh:user:{0}:lang".format(ghuser), 0, 5, withscores=True)

    days, hours, connections, langs = pipe.execute()

    # Build the daily schedule histogram.
    day_hist = [0] * 7
    for k, v in days.iteritems():
        day_hist[int(k)] = int(v)

    # Build the hourly histogram.
    hour_hist = [0] * 24
    for k, v in hours.iteritems():
        hour_hist[int(k)] = int(v)

    # Figure out the timezone.
    tz = None
    location = user.get("location")
    if location:
        pars = {"location": location,
                "maxResults": 1,
                "thumbMaps": False}
        r = requests.get(mqapi_url, params=pars)
        if r.status_code == requests.codes.ok:
            resp = r.json().get("results", [])
            if len(resp):
                locs = resp[0].get("locations", [])
                if len(locs):
                    latlng = locs[0].get("latLng", {})
                    if "lat" in latlng and "lng" in latlng:
                        r = requests.get(tzapi_url.format(**latlng))
                        if r.status_code == requests.codes.ok:
                            matches = tz_re.findall(r.text)
                            if len(matches):
                                tz = int(matches[0])

    template_args = {"name": name,
                     "days": ",".join(map(unicode, day_hist)),
                     "hours": ",".join(map(unicode, hour_hist)),
                     "connections": connections,
                     "languages": langs,
                     "location": location,
                     "tz": tz,
                     }

    return flask.render_template("report.html", **template_args)
