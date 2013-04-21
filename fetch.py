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
from itertools import product
from datetime import datetime, timedelta
import redis
import requests

base_url = "http://data.githubarchive.org/{date}-{n}.json.gz"
fmt = "%Y-%m-%d"
today = datetime.utcnow()
dt = timedelta(-1)

_path = os.path.dirname(os.path.abspath(__file__))
languages = [l.strip() for l in open(os.path.join(_path, "languages.txt"))]
evttypes = [l.strip() for l in open(os.path.join(_path, "evttypes.txt"))]

redis_pool = redis.ConnectionPool()

times = ["night", "night", "morning", "afternoon", "evening", "evening"]


def run(days, n):
    strt = time.time()
    url = base_url.format(date=(today + days * dt).strftime(fmt), n=n)
    r = requests.get(url)
    if r.status_code == requests.codes.ok:
        with gzip.GzipFile(fileobj=StringIO(r.content)) as f:
            events = [json.loads(l) for l in f]

        for event in events:
            repo = event.get("repository", {})
            repo_name = repo.get("name")
            evttype = event.get("type")
            actor = event.get("actor")
            timestamp = event.get("created_at")

            try:
                language = languages.index(repo.get("language"))
            except ValueError:
                language = -1

            # Parse the timestamp.
            timestamp, utc_offset = timestamp[:-6], timestamp[-6:-3]
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
            timestamp += timedelta(hours=float(utc_offset))
            weekday, hour = timestamp.strftime("%w %H").split()
            hour = int(hour)

            # Add to redis.
            key = "gh:events:{0}".format(actor)
            r = redis.Redis(connection_pool=redis_pool)
            pipe = r.pipeline(transaction=False)

            # Update the event stats.
            pipe.hincrby(key, "total", 1)
            pipe.hincrby(key, "day:{0}".format(weekday), 1)
            pipe.hincrby(key, "lang:{0}".format(language), 1)
            pipe.hincrby(key, evttype, 1)
            pipe.hincrby(key, times[(hour - hour % 4) // 4], 1)

            # Update the repo stats.
            pipe.zincrby("gh:repos:{0}".format(actor), repo_name, 1)

            # Execute the pipe.
            pipe.execute()

        print("Processed {0} events in {1} seconds"
              .format(len(events), time.time() - strt))


if __name__ == "__main__":
    jobs = [gevent.spawn(run, *a) for a in product(range(1, 2), range(24))]
    gevent.joinall(jobs)
