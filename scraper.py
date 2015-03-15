#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = []

import re
import json
import psycopg2
import requests
from datetime import datetime

API_URL = "https://api.github.com"
CLIENT_ID = "af8ac41d63ad3e7268e8"
CLIENT_SECRET = "b33fe44f53fd2a903891ceb78551121f59039fa5"


def get_db():
    return psycopg2.connect(database="osrc")


def gh_request(path, method="GET", etag=None, **params):
    # Build the URL, header, and parameter set.
    url = API_URL + path
    headers = {"User-Agent": "osrc"}
    if etag is not None:
        headers["If-None-Match"] = etag
    params["client_id"] = params.get("client_id", CLIENT_ID)
    params["client_secret"] = params.get("client_secret", CLIENT_SECRET)

    # Execute the request.
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    return r


def parse_date(dt):
    return datetime(*map(int, re.split(r"[^\d]", dt)[:-1]))


def get_event_list():
    with open("events.json", "r") as f:
        return json.load(f)
    # events = gh_request("/events").json()
    # with open("events.json", "w") as f:
    #     json.dump(events, f)


def _upsert(c, tbl, up_cmd, where, ins_cmd, *args):
    up_cmd = "update {0} {1} where {2}".format(tbl, up_cmd, where)
    a = ",".join(["%s"] * len(args))
    ins_cmd = "insert into {0}({1}) values({2})".format(tbl, ins_cmd, a)

    while True:
        c.execute(up_cmd, args)
        if c.rowcount == 0:
            try:
                c.execute(ins_cmd, args)
            except psycopg2.IntegrityError:
                continue
        return


def parse_event(event):
    evttype = event["type"]
    user = event["actor"]
    repo = event["repo"]
    dt = parse_date(event["created_at"])
    day, hour = map(int, dt.strftime("%w %H").split())

    with get_db() as conn:
        c = conn.cursor()

        # Upsert the actor entry.
        _upsert(c, "gh_users", "set login=%s,avatar_url=%s",
                "user_id=%s", "login,avatar_url,user_id",
                user["login"], user["avatar_url"], user["id"])

        # Upsert the repo entry.
        _upsert(c, "gh_repos", "set name=%s", "repo_id=%s", "name,repo_id",
                repo["name"], repo["id"])

        # Upsert the event stats.
        _upsert(c, "gh_event_stats", "set count=count+1,last_modified=%s",
                "user_id=%s and repo_id=%s and evttype=%s",
                "last_modified,user_id,repo_id,evttype",
                dt, user["id"], repo["id"], evttype)

        # Upsert the event day.
        _upsert(c, "gh_event_days", "set count=count+1",
                "user_id=%s and evttype=%s and day=%s",
                "user_id,evttype,day",
                user["id"], evttype, day)

        # Upsert the event hour.
        _upsert(c, "gh_event_hours", "set count=count+1",
                "user_id=%s and evttype=%s and hour=%s",
                "user_id,evttype,hour",
                user["id"], evttype, hour)
    # return

    # # Get the repository Etag if it exists.
    # etag = None
    # with get_db() as conn:
    #     c = conn.cursor()
    #     c.execute("select etag from gh_repos where repo_id=%s",
    #               (event["repo"]["id"], ))
    #     r = c.fetchone()
    #     if r is not None:
    #         etag = r[0]

    # # Download the full repository record.
    # r = gh_request("/repos/" + event["repo"]["name"], etag=etag)

    # # The repository is currently unchanged.
    # if r.status_code == 304:
    #     print("Unchanged")
    #     return

    # # Parse the repository record.
    # repo = r.json()
    # with get_db() as conn:
    #     c = conn.cursor()

    #     # Upsert the owner entry.
    #     owner = repo["owner"]
    #     _upsert(c, "gh_users", "set login=%s,user_type=%s,avatar_url=%s",
    #             "user_id=%s", "login,user_type,user_id",
    #             owner["login"], owner["type"], owner["avatar_url"],
    #             owner["id"])

    #     # Upsert the repo entry.
    #     etag = r.headers["etag"]
    #     _upsert(c, "gh_repos",
    #             "set owner_id=%s,name=%s,description=%s,language=%s,"
    #             "star_count=%s,watcher_count=%s,fork_count=%s,issue_count=%s,"
    #             "updated=%s,etag=%s", "repo_id=%s",
    #             "owner_id,name,description,language,star_count,watcher_count,"
    #             "fork_count,issue_count,updated,etag,repo_id",
    #             owner["id"], repo["name"], repo["description"],
    #             repo["language"], repo["stargazers_count"],
    #             repo["subscribers_count"], repo["forks_count"],
    #             repo["open_issues_count"], parse_date(repo["updated_at"]),
    #             etag, repo["id"])


if __name__ == "__main__":
    map(parse_event, get_event_list())
