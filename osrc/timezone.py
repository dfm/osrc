#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["estimate_timezone"]

import re
import flask
import logging
import requests

from .database import get_pipeline, format_key

tz_re = re.compile(r"<offset>([\-0-9]+)</offset>")
mqapi_url = "http://open.mapquestapi.com/geocoding/v1/address"
tzapi_url = "https://maps.googleapis.com/maps/api/timezone/json"
goapi_url = "https://maps.googleapis.com/maps/api/geocode/json"


def _google_geocode(location):
    # Check for quota limits.
    pipe = get_pipeline()
    usage_key = format_key("google_usage_limit")
    usage = pipe.get(usage_key).execute()[0]
    if usage is not None:
        logging.warn("Skipping Google geocode request for usage limits.")
        return None

    # Submit the request.
    params = dict(
        address=location,
        sensor="false",
        key=flask.current_app.config["GOOGLE_KEY"],
    )
    r = requests.get(goapi_url, params=params)
    if r.status_code != requests.codes.ok:
        logging.error(r.content)
        return None

    data = r.json()

    # Try not to go over usage limits.
    status = data.get("status", None)
    if status == "OVER_QUERY_LIMIT":
        pipe.set(usage_key, 1).expire(usage_key, 60*60)
        pipe.execute()
        return None

    # Parse the results.
    results = data.get("results", [])
    if not len(results):
        return None

    # Find the coordinates.
    loc = results[0].get("geometry", {}).get("location", None)
    return loc


def _mq_geocode(location):
    params = {"location": location, "thumbMaps": False, "maxResults": 1}
    r = requests.get(mqapi_url, params=params)
    if r.status_code != requests.codes.ok:
        return None

    # Parse the results.
    results = r.json().get("results", [])
    if not len(results):
        return None

    # Find the coordinates.
    locs = results[0].get("locations", {})
    if not len(locs):
        return None

    loc = locs[0].get("latLng", None)
    return loc


def geocode(location):
    if not len(location):
        return None

    # Try Google first.
    try:
        loc = _google_geocode(location)
    except Exception as e:
        logging.warn("Google geocoding failed with:\n{0}".format(e))
        loc = None

    # Fall back onto MapQuest.
    if loc is None:
        try:
            loc = _mq_geocode(location)
        except Exception as e:
            logging.warn("MQ geocoding failed with:\n{0}".format(e))
            loc = None

    return loc


def estimate_timezone(location):
    # Start by geocoding the location string.
    loc = geocode(location)
    if loc is None:
        logging.warn("Couldn't resolve location for {0}".format(location))
        return None

    # Resolve the timezone associated with these coordinates.
    params = dict(
        key=flask.current_app.config["GOOGLE_KEY"],
        location="{lat},{lng}".format(**loc),
        timestamp=0,
        sensor="false",
    )
    r = requests.get(tzapi_url, params=params)
    if r.status_code != requests.codes.ok:
        logging.error("Timezone zone request failed:\n{0}".format(r.url))
        return None

    result = r.json().get("rawOffset", None)
    if result is None:
        return None
    return int(result / (60*60))
