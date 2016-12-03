# -*- coding: utf-8 -*-

__all__ = ["geocode", "timezone"]

import flask
import requests

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TIMEZONE_URL = "https://maps.googleapis.com/maps/api/timezone/json"


def geocode(address, **params):
    headers = {"User-Agent": "osrc"}
    params["key"] = params.get("key", flask.current_app.config["GOOGLE_KEY"])
    params["address"] = address
    r = requests.get(GEOCODE_URL, headers=headers, params=params)
    if r.status_code != requests.codes.ok:
        return None

    resp = r.json()
    if resp["status"] != "OK":
        return None
    return resp["results"][0].get("geometry", {}).get("location", None)


def timezone(address):
    latlng = geocode(address)
    if latlng is None:
        return None

    headers = {"User-Agent": "osrc"}
    params = dict(
        key=flask.current_app.config["GOOGLE_KEY"],
        location="{lat},{lng}".format(**latlng),
        timestamp=0,
    )

    r = requests.get(TIMEZONE_URL, headers=headers, params=params)
    if r.status_code != requests.codes.ok:
        return None

    resp = r.json()
    if resp["status"] != "OK" or "rawOffset" not in resp:
        return None
    return latlng, int(resp["rawOffset"] / 3600)
