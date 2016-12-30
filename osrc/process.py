# -*- coding: utf-8 -*-

from datetime import datetime

from . import google
from .utils import load_json_resource
from .models import db, User, Repo

__all__ = [
    "parse_datetime", "process_repo", "process_user",
]


def parse_datetime(dt, fmt="%Y-%m-%dT%H:%M:%SZ"):
    return datetime.strptime(dt, fmt) if dt is not None else None


def process_repo(repo, etag=None):
    if "organization" in repo:
        process_user(repo["organization"])
    if "parent" in repo:
        process_repo(repo["parent"])
    if "source" in repo:
        process_repo(repo["source"])

    # Get the owner.
    if "owner" in repo:
        name = repo["name"]
        owner = process_user(repo["owner"])
        fullname = "{0}/{1}".format(owner.login, name)
    else:
        fullname = repo["name"]
        name = fullname.split("/")[-1]
        owner = None

    # Parse the date.
    updated = parse_datetime(repo.get("updated_at"))

    repo_obj = Repo.query.filter_by(id=repo["id"]).first()
    if repo_obj is None:
        repo_obj = Repo(
            id=repo["id"],
            owner=owner,
            name=name,
            fullname=fullname,
            description=repo.get("description"),
            star_count=repo.get("stargazers_count"),
            watcher_count=repo.get("subscribers_count"),
            fork_count=repo.get("forks_count"),
            issues_count=repo.get("open_issues_count"),
            last_updated=updated,
            language=repo.get("language"),
            etag=etag,
        )
        db.session.add(repo_obj)
    else:
        repo_obj.name = name
        repo_obj.fullname = fullname
        repo_obj.owner = owner
        repo_obj.language = repo.get("language", repo_obj.language)
        repo_obj.description = repo.get("description", repo_obj.description)
        repo_obj.star_count = repo.get("stargazers_count", repo_obj.star_count)
        repo_obj.watcher_count = repo.get("subscribers_count",
                                          repo_obj.watcher_count)
        repo_obj.fork_count = repo.get("forks_count", repo_obj.fork_count)
        repo_obj.issues_count = repo.get("open_issues_count",
                                         repo_obj.issues_count)
        if updated is not None:
            repo_obj.last_updated = updated
        if etag is not None:
            repo_obj.etag = etag
    return repo_obj


def process_user(user, etag=None):
    user_obj = User.query.filter_by(id=user["id"]).first()
    update_tz = True
    if user_obj is None:
        # Make sure that users who opted out previously have active=False.
        optouts = load_json_resource("optout.json")

        user_obj = User(
            id=user["id"],
            user_type=user.get("type", "User"),
            name=user.get("name"),
            login=user["login"],
            location=user.get("location"),
            avatar_url=user["avatar_url"],
            active=user["login"].lower() not in optouts,
            etag=etag,
        )

        db.session.add(user_obj)
    else:
        update_tz = user_obj.location != user.get("location",
                                                  user_obj.location)
        user_obj.user_type = user.get("type", user_obj.user_type)
        user_obj.name = user.get("name", user_obj.name)
        user_obj.login = user.get("login", user_obj.login)
        user_obj.location = user.get("location", user_obj.location)
        user_obj.avatar_url = user.get("avatar_url", user_obj.avatar_url)
        if etag is not None:
            user_obj.etag = etag

    # Update the timezone.
    if update_tz and user_obj.location is not None:
        r = google.timezone(user_obj.location)
        if r is not None:
            latlng, tz = r
            user_obj.timezone = tz
            user_obj.lat = latlng["lat"]
            user_obj.lng = latlng["lng"]

    return user_obj
