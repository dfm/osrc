#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_user_info"]

import flask
import requests

from .timezone import estimate_timezone
from .database import get_pipeline, format_key

ghapi_url = "https://api.github.com/users/{username}"


def get_user_info(username):
    # Normalize the username.
    user = username.lower()

    # Get the cached information.
    pipe = get_pipeline()
    pipe.get(format_key("user:{0}:name".format(user)))
    pipe.get(format_key("user:{0}:etag".format(user)))
    pipe.get(format_key("user:{0}:gravatar".format(user)))
    pipe.get(format_key("user:{0}:tz".format(user)))
    name, etag, gravatar, timezone = pipe.execute()
    if name is not None:
        name = name.decode("utf-8")

    # Work out the authentication headers.
    auth = {}
    client_id = flask.current_app.config.get("GITHUB_ID", None)
    client_secret = flask.current_app.config.get("GITHUB_SECRET", None)
    if client_id is not None and client_secret is not None:
        auth["client_id"] = client_id
        auth["client_secret"] = client_secret

    # Perform a conditional fetch on the database.
    headers = {}
    if etag is not None:
        headers = {"If-None-Match": etag}

    r = requests.get(ghapi_url.format(username=username), params=auth,
                     headers=headers)
    code = r.status_code
    if code != 304 and code == requests.codes.ok:
        data = r.json()
        name = data.get("name") or data.get("login") or username
        etag = r.headers["ETag"]
        gravatar = data.get("gravatar_id", "none")
        location = data.get("location", None)
        if location is not None:
            tz = estimate_timezone(location)
            if tz is not None:
                timezone = tz

        # Update the cache.
        pipe.set(format_key("user:{0}:name".format(user)), name)
        pipe.set(format_key("user:{0}:etag".format(user)), etag)
        pipe.set(format_key("user:{0}:gravatar".format(user)), gravatar)
        if timezone is not None:
            pipe.set(format_key("user:{0}:tz".format(user)), timezone)
        pipe.execute()

    return {
        "name": name.decode("utf-8") if name is not None else username,
        "gravatar": gravatar if gravatar is not None else "none",
        "timezone": int(timezone) if timezone is not None else None,
    }
