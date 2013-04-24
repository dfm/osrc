#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["process"]

import re
import sys
import gzip
import json
import time
import redis
from datetime import date
from multiprocessing import Pool

redis_pool = redis.ConnectionPool()

date_re = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]+)\.json.gz")


def process(filename):
    # Figure out the day of the week from the filename (this is probably not
    # always right but it'll do).
    year, month, day, hour = map(int, date_re.findall(filename)[0])
    weekday = date(year=year, month=month, day=day).strftime("%w")

    # Set up a redis pipeline.
    r = redis.Redis(connection_pool=redis_pool)
    pipe = r.pipeline(transaction=False)

    # Unzip and load the file.
    strt = time.time()
    with gzip.GzipFile(filename) as f:
        # One event per line.
        for n, line in enumerate(f):
            # Parse the JSON of this event.
            try:
                event = json.loads(line.decode("utf-8", errors="ignore"))
            except:
                print("Failed on line {0} of {1}-{2:02d}-{3:02d}-{4}"
                      .format(n, year, month, day, hour))
                continue

            # Get the user involved and skip if there isn't one.
            actor = event["actor"]
            if actor is None:
                # This was probably an anonymous event (like a gist event).
                continue

            # Normalize the user name.
            actor = actor.lower()

            # Get the type of event.
            evttype = event["type"]

            # Old skool.
            nevents = 1

            # Can this be called a "contribution"?
            contribution = evttype in ["IssuesEvent", "PullRequestEvent",
                                       "PushEvent", "IssueCommentEvent",
                                       "PullRequestReviewCommentEvent",
                                       "CommitCommentEvent"]

            # Increment the global sum histograms.
            pipe.incr("gh:total", nevents)
            pipe.hincrby("gh:day", weekday, nevents)
            pipe.hincrby("gh:hour", hour, nevents)
            pipe.zincrby("gh:user", actor, nevents)
            pipe.zincrby("gh:event", evttype, nevents)

            # User schedule histograms.
            pipe.hincrby("gh:user:{0}:day".format(actor), weekday, nevents)
            pipe.hincrby("gh:user:{0}:hour".format(actor), hour, nevents)

            # User event type histogram.
            pipe.zincrby("gh:user:{0}:event".format(actor), evttype, nevents)
            pipe.zincrby("gh:user:{0}:event:{1}:day".format(actor, evttype),
                         weekday, nevents)
            pipe.zincrby("gh:user:{0}:event:{1}:hour".format(actor, evttype),
                         hour, nevents)

            # Parse the name and owner of the affected repository.
            repo = event.get("repository", {})
            owner, name = (repo.get("owner"), repo.get("name"))
            if owner and name:
                repo_name = "{0}/{1}".format(owner, name)
                pipe.zincrby("gh:repo", repo_name, nevents)

                # Is the user contributing to their own project.
                if owner == actor:
                    pipe.zincrby("gh:user:{0}:repo".format(actor),
                                 repo_name, nevents)

                # If not, save all sorts of goodies.
                else:
                    if contribution:
                        pipe.zincrby("gh:contribution", repo_name, nevents)
                        pipe.zincrby("gh:user:{0}:contribution".format(actor),
                                     repo_name, nevents)

                    # How connected are these two users?
                    pipe.zincrby("gh:user:{0}:connection".format(actor),
                                 owner, nevents)
                    pipe.zincrby("gh:user:{0}:connection".format(owner),
                                 actor, nevents)

                    # Update the global count of connections.
                    pipe.incr("gh:connection", nevents)
                    pipe.zincrby("gh:connection:user", actor, nevents)
                    pipe.zincrby("gh:connection:user", owner, nevents)

                # Do we know what the language of the repository is?
                language = repo.get("language")
                if language:
                    # Which are the most popular languages?
                    pipe.zincrby("gh:lang", language, nevents)

                    # What are a user's favorite languages?
                    pipe.zincrby("gh:user:{0}:lang".format(actor), language,
                                 nevents)

                    # Who are the most important users of a language?
                    if contribution:
                        pipe.zincrby("gh:lang:{0}:user".format(language),
                                     actor, nevents)

        pipe.execute()

        print("Processed {0} events in {1} [{2:.2f} seconds]"
              .format(n, filename, time.time() - strt))


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: process.py /path/to/data/*.json.gz")
        sys.exit(1)

    pool = Pool(24)
    pool.map(process, sys.argv[1:])
