# -*- coding: utf-8 -*-

import flask
import requests
from sqlalchemy import func

from .models import db, User, Repo
from .process import process_user, process_repo
from .redis import format_key, get_connection, get_pipeline

__all__ = ["gh_request", "get_user", "get_repo"]

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

def update_cache(flag, obj):
    # Update the cache flag.
    cache_key = format_key("c:{0}:{1}".format(flag, obj.id))
    with get_pipeline() as pipe:
        pipe.setbit(cache_key, 0, 1)
        pipe.expire(cache_key, 24 * 60 * 60)
        pipe.execute()


def get_user(username=None, id=None, user=None, use_cache=True):
    if user is None:
        if id is not None:
            user = User.query.filter(User.id == id).first()
            if user is None:
                return None
            username = user.login
        elif username is not None:
            user = User.query.filter(
                func.lower(User.login) == func.lower(username)).first()
        else:
            return None

    # Check to see if the cache is up to date.
    if use_cache and user is not None:
        cache_key = format_key("c:u:{0}".format(user.id))
        conn = get_connection()
        bit = conn.getbit(cache_key, 0)
        if bit:
            return user

    # Update the user information using the API.
    etag = None if user is None else user.etag
    username = user.login if username is None else username
    try:
        r = gh_request("/users/{0}".format(username), etag=etag)
    except requests.exceptions.ConnectionError:
        if user is not None:
            return user
        raise

    # Save the new information.
    if r.status_code == 304:
        update_cache("u", user)
        return user
    elif r.status_code != requests.codes.ok:
        if user is None:
            flask.abort(r.status_code)
        return user
    user = process_user(r.json(), etag=r.headers["ETag"])
    db.session.commit()
    update_cache("u", user)
    return user


def get_repo(fullname=None, id=None, repo=None, use_cache=True):
    if repo is None:
        if id is not None:
            repo = Repo.query.filter(Repo.id == id).first()
            if repo is None:
                return None
            fullname = repo.fullname
        elif fullname is not None:
            repo = Repo.query.filter(
                func.lower(Repo.fullname) == func.lower(fullname)).first()
        else:
            return None

    # Check to see if the cache is up to date.
    if use_cache and repo is not None:
        cache_key = format_key("c:r:{0}".format(repo.id))
        conn = get_connection()
        bit = conn.getbit(cache_key, 0)
        if bit:
            return repo

    # Update the user information using the API.
    etag = None if repo is None else repo.etag
    fullname = repo.fullname if fullname is None else fullname
    try:
        r = gh_request("/repos/{0}".format(fullname), etag=etag)
    except requests.exceptions.ConnectionError:
        if repo is not None:
            return repo
        raise

    # Save the new information.
    if r.status_code == 304:
        update_cache("r", repo)
        return repo
    elif r.status_code != requests.codes.ok:
        if repo is None:
            flask.abort(r.status_code)
        return repo
    repo = process_repo(r.json(), etag=r.headers["ETag"])
    db.session.commit()
    update_cache("r", repo)
    return repo
