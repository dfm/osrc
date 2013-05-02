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

from ghdata.build_index import get_neighbors


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
    return flask.render_template("index.html")


def get_tz(location):
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
                            return int(matches[0])


@app.route("/<username>")
def user(username):
    # Start by getting the user information from the API.
    r = requests.get(ghapi_url + "/users/" + username, params=flask.g.ghauth)
    if r.status_code != requests.codes.ok:
        logging.error("GitHub API failed: {0}".format(r.status_code))
        logging.error(r.text)
        flask.abort(404)

    # Parse the JSON response.
    user = r.json()

    # Get the user's name or login.
    name = user.get("name") or user.get("login") or username

    # Check timezone.
    ghuser = username.lower()
    if not flask.g.redis.exists("gh:user:{0}:tz".format(ghuser)):
        location = user.get("location")
        if location:
            flask.g.redis.set("gh:user:{0}:tz".format(ghuser),
                              get_tz(location))

    return flask.render_template("index.html",
                                 gravatar=user.get("gravatar_id", "none"),
                                 name=name,
                                 firstname=name.split()[0],
                                 username=username)


def make_hist(data, size, offset=None):
    if offset is None:
        offset = 0
    result = [0] * size
    for k, v in data:
        val = float(v)
        i = int(k) + offset
        while (i < 0):
            i += size
        result[i % size] = val
    return result


@app.route("/<username>/stats")
def get_stats(username):
    ghuser = username.lower()

    evttypes = flask.g.redis.zrevrangebyscore("gh:user:{0}:event"
                                              .format(ghuser), "+inf", 4)

    # Get the user histogram.
    pipe = flask.g.redis.pipeline()

    # Get the time zone.
    pipe.get("gh:user:{0}:tz".format(ghuser))

    # Get the total number of events.
    pipe.zscore("gh:user", ghuser)

    # Get the daily schedule for each type of event.
    [pipe.hgetall("gh:user:{0}:event:{1}:day".format(ghuser, e))
     for e in evttypes]

    # Get the hourly schedule for each type of event.
    [pipe.hgetall("gh:user:{0}:event:{1}:hour".format(ghuser, e))
     for e in evttypes]

    # Get the distribution of languages contributed to.
    pipe.zrevrange("gh:user:{0}:lang".format(ghuser), 0, -1, withscores=True)

    # Get the vulgarity (and vulgar rank) of the user.
    pipe.zrevrange("gh:user:{0}:curse".format(ghuser), 0, -1, withscores=True)
    pipe.zcard("gh:curse:user")
    pipe.zrevrank("gh:curse:user", ghuser)

    # Fetch the data from the database.
    raw = pipe.execute()

    # Get the general stats.
    tz = int(raw[0]) if raw[0] is not None else None
    total = int(raw[1]) if raw[1] is not None else 0

    # Get the schedule histograms.
    n, m = 2, len(evttypes)
    week = zip(*[make_hist(d.iteritems(), 7)
                 for k, d in zip(evttypes, raw[n:n + m])])
    offset = tz + 8 if tz is not None else 0
    day = zip(*[make_hist(d.iteritems(), 24, offset=offset)
                for k, d in zip(evttypes, raw[n + m:n + 2 * m])])

    # Get the language proportions.
    n = n + 2 * m
    langs = raw[n]
    curses = raw[n + 1]

    # Parse the vulgarity factor.
    vulgarity = None
    try:
        vulgarity = int(100 * float(raw[n + 3]) / float(raw[n + 2])) + 1
    except:
        pass

    # Get language rank.
    langrank = None
    if len(langs):
        lang = langs[0][0]

        # Made up number. How many contributions count as enough? 50? Sure.
        pipe.zcount("gh:lang:{0}:user".format(lang), 50, "+inf")
        pipe.zrevrank("gh:lang:{0}:user".format(lang), ghuser)
        ltot, lrank = pipe.execute()

        # This user is in the top N percent of users of language "lang".
        try:
            langrank = (lang, int(100 * float(lrank) / float(ltot))) + 1
        except:
            pass

    # Get neighbors.
    # neighbors = get_neighbors(ghuser)

    # Format the results.
    results = {"events": evttypes}
    results["tz"] = tz
    results["total"] = total
    results["week"] = week
    results["day"] = day
    results["languages"] = langs
    results["language_rank"] = langrank
    results["curses"] = curses
    results["vulgarity"] = vulgarity

    return json.dumps(results)
