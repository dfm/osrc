#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = []

import re
import time
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
    etag, last_id = None, 0
    with get_db() as conn:
        c = conn.cursor()
        c.execute("select etag,last_id from osrc_status where status_id=1")
        r = c.fetchone()
        if r is not None:
            etag, last_id = r

    while True:
        strt = time.time()
        r = gh_request("/events", etag=etag, per_page=100)
        count = 0
        if r.status_code != 304:
            # Loop over the events and yield them until we hit the last id.
            events = r.json()
            for evt in events:
                if int(evt["id"]) <= last_id:
                    break
                yield evt
                count += 1
            print(count)

            # Update the etag and modified stuff.
            etag = r.headers["etag"]
            last_id = int(events[0]["id"])
            with get_db() as conn:
                c = conn.cursor()
                _upsert(c, "osrc_status",
                        "set etag=%s,last_updated=%s,last_id=%s",
                        "status_id=%s", "etag,last_updated,last_id,status_id",
                        r.headers["etag"], datetime.now(), last_id, 1)

        dt = int(r.headers["x-poll-interval"]) - (time.time() - strt)
        print(dt)
        time.sleep(dt)


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


if __name__ == "__main__":
    events = get_event_list()
    map(parse_event, events)
