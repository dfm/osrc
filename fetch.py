#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = []

import gevent
from gevent import monkey
monkey.patch_all()

import gzip
import json
import time
from StringIO import StringIO
from datetime import datetime, timedelta
import redis
import requests

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
            actor = event.get("actor")
            if actor:
                actor = actor.lower()
            else:
                continue

            repo = event.get("repository", {})
            repo_name = (repo.get("owner"), repo.get("name"))
            if all(repo_name):
                repo_name = "/".join(repo_name)
            else:
                continue

            evttype = event["type"]
            language = repo.get("language")

            # Add to redis.
            r = redis.Redis(connection_pool=redis_pool)
            pipe = r.pipeline(transaction=False)
            pipe.zincrby("gh:users", actor, 1)
            pipe.zincrby("gh:events:{0}".format(actor), evttype, 1)
            pipe.zincrby("gh:sums:events", evttype, 1)
            pipe.zincrby("gh:days:{0}".format(actor), weekday, 1)
            pipe.zincrby("gh:sums:days", weekday, 1)
            if repo_name:
                pipe.zincrby("gh:repos:{0}".format(actor), repo_name, 1)
                pipe.zincrby("gh:sums:repos", repo_name, 1)
            if language:
                pipe.zincrby("gh:langs:{0}".format(actor), language, 1)
                pipe.zincrby("gh:sums:langs", language, 1)
            pipe.execute()

        print("Processed {0} events in {1} seconds"
              .format(len(events), time.time() - strt))


if __name__ == "__main__":
    for day in range(14, 31):
        jobs = [gevent.spawn(run, day, n) for n in range(24)]
        gevent.joinall(jobs)
