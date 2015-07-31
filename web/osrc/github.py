# -*- coding: utf-8 -*-

__all__ = ["gh_request", "get_user", "get_repo"]

import flask
import requests
from sqlalchemy import func

from .models import db, User, Repo
from .process import process_user, process_repo

API_URL = "https://api.github.com"


def gh_request(path, method="GET", etag=None, **params):
    # Build the URL, header, and parameter set.
    url = API_URL + path
    headers = {
        "User-Agent": "osrc",
        "Accept": "application/vnd.github.v3+json",
    }
    if etag is not None:
        headers["If-None-Match"] = etag
    params["client_id"] = params.get(
        "client_id", flask.current_app.config["GITHUB_ID"])
    params["client_secret"] = params.get(
        "client_secret", flask.current_app.config["GITHUB_SECRET"])

    # Execute the request.
    r = requests.get(url, headers=headers, params=params)
    return r


def get_user(username):
    user = User.query.filter(
        func.lower(User.login) == func.lower(username)).first()
    etag = None if user is None else user.etag
    r = gh_request("/users/{0}".format(username), etag=etag)
    if r.status_code == 304:
        return user
    elif r.status_code != requests.codes.ok:
        flask.abort(r.status_code)
    user = process_user(r.json(), etag=r.headers["ETag"])
    db.session.commit()
    return user


def get_repo(fullname):
    repo = Repo.query.filter(
        func.lower(Repo.fullname) == func.lower(fullname)) \
        .order_by(Repo.id.desc()).first()
    etag = None if repo is None else repo.etag
    r = gh_request("/repos/{0}".format(fullname), etag=etag)
    if r.status_code == 304:
        return repo
    elif r.status_code != requests.codes.ok:
        flask.abort(r.status_code)
    user = process_repo(r.json(), etag=r.headers["ETag"])
    db.session.commit()
    return user
