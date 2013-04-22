#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = []

import gevent
from gevent import monkey
monkey.patch_all()

import os
import gzip
import json
import time
from StringIO import StringIO
from datetime import datetime, timedelta
import redis
import requests

GITHUB_ID = os.environ["GITHUB_ID"]
GITHUB_SECRET = os.environ["GITHUB_SECRET"]
GITHUB_AUTH = {"client_id": GITHUB_ID, "client_secret": GITHUB_SECRET}

base_url = "http://data.githubarchive.org/{date}-{n}.json.gz"
fmt = "%Y-%m-%d"
today = datetime.utcnow()
dt = timedelta(-1)

redis_pool = redis.ConnectionPool()


def run(days, n):
    strt = time.time()
    target_date = today + (days + 1) * dt
    weekday = target_date.strftime("%w")
    url = base_url.format(date=target_date.strftime(fmt), n=n)
    r = requests.get(url)
    if r.status_code == requests.codes.ok:
        with gzip.GzipFile(fileobj=StringIO(r.content)) as f:
            events = [json.loads(l.decode("utf-8", errors="ignore"))
                      for l in f]

        for event in events:
            # Get the user name of the active user.
            actor = event.get("actor")
            if actor:
                actor = actor.lower()
            else:
                continue

            # Parse the name and owner of the affected repository.
            repo = event.get("repository", {})
            owner, name = (repo.get("owner"), repo.get("name"))
            repo_name = None
            if owner and name:
                repo_name = "{0}/{1}".format(owner, name)

            # Get the type of event and repository language.
            evttype = event["type"]
            language = repo.get("language")

            # How many events are included with this listing?
            nevents = 1
            if evttype == "PushEvent":
                nevents = event["payload"]["size"]

            # Add to redis.
            r = redis.Redis(connection_pool=redis_pool)
            pipe = r.pipeline(transaction=False)

            # Global counts.
            pipe.zincrby("gh:day", weekday, nevents)
            pipe.zincrby("gh:user", actor, nevents)
            pipe.zincrby("gh:event", evttype, nevents)

            # User schedule histogram.
            pipe.zincrby("gh:user:{0}:day".format(actor), weekday, nevents)

            # User event type histogram.
            pipe.zincrby("gh:user:{0}:event".format(actor), evttype, nevents)

            # User event type day-by-day breakdown.
            pipe.zincrby("gh:user:{0}:event:{1}:day".format(actor, evttype),
                         weekday, nevents)

            # If a specific repository was harmed in the making of this event.
            if repo_name:
                pipe.zincrby("gh:repo", repo_name, nevents)

                # Is the user contributing to their own project.
                if owner == actor:
                    pipe.zincrby("gh:user:{0}:ownrepo".format(actor),
                                 repo_name, nevents)
                else:
                    pipe.zincrby("gh:user:{0}:otherrepo".format(actor),
                                 repo_name, nevents)

            # Do we know what the language of the repository is?
            if language:
                pipe.zincrby("gh:lang", language, nevents)
                pipe.zincrby("gh:user:{0}:lang".format(actor), language,
                             nevents)

            pipe.execute()

        print("Processed {0} events in {1} seconds"
              .format(len(events), time.time() - strt))


if __name__ == "__main__":
    for day in range(31):
        jobs = [gevent.spawn(run, day, n) for n in range(24)]
        gevent.joinall(jobs)
