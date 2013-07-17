#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["process"]

import re
import os
import sys
import gzip
import json
import time
import redis
from datetime import date
from multiprocessing import Pool

redis_pool = redis.ConnectionPool(port=int(os.environ.get("OSRC_REDIS_PORT",
                                                          6380)))

date_re = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]+)\.json.gz")

sw_re = re.compile("|".join([r"(?:\b{0}\b)".format(l.strip())
                             for l in open("osrc/static/swears.txt")]))


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
            attrs = event.get("actor_attributes", {})
            if actor is None or attrs.get("type") != "User":
                # This was probably an anonymous event (like a gist event)
                # or an organization event.
                continue

            # Is this an organization?

            # Normalize the user name.
            key = actor.lower()

            # Get the type of event.
            evttype = event["type"]

            # Old skool.
            nevents = 1

            # Can this be called a "contribution"?
            contribution = evttype in ["IssuesEvent", "PullRequestEvent",
                                       "PushEvent"]

            # Increment the global sum histograms.
            pipe.incr("gh:total", nevents)
            pipe.hincrby("gh:day", weekday, nevents)
            pipe.hincrby("gh:hour", hour, nevents)
            pipe.zincrby("gh:user", key, nevents)
            pipe.zincrby("gh:event", evttype, nevents)

            # Event histograms.
            pipe.hincrby("gh:event:{0}:day".format(evttype), weekday, nevents)
            pipe.hincrby("gh:event:{0}:hour".format(evttype), hour, nevents)

            # User schedule histograms.
            pipe.hincrby("gh:user:{0}:day".format(key), weekday, nevents)
            pipe.hincrby("gh:user:{0}:hour".format(key), hour, nevents)

            # User event type histogram.
            pipe.zincrby("gh:user:{0}:event".format(key), evttype, nevents)
            pipe.hincrby("gh:user:{0}:event:{1}:day".format(key, evttype),
                         weekday, nevents)
            pipe.hincrby("gh:user:{0}:event:{1}:hour".format(key, evttype),
                         hour, nevents)

            # Parse the name and owner of the affected repository.
            repo = event.get("repository", {})
            owner, name, org = (repo.get("owner"), repo.get("name"),
                                repo.get("organization"))
            if owner and name:
                repo_name = "{0}/{1}".format(owner, name)
                pipe.zincrby("gh:repo", repo_name, nevents)

                # Is the user contributing to their own project.
                okey = owner.lower()
                if okey == key:
                    pipe.zincrby("gh:user:{0}:repo".format(key),
                                 repo_name, nevents)

                # If not, save all sorts of goodies.
                else:
                    if contribution:
                        pipe.zincrby("gh:contribution", repo_name, nevents)
                        pipe.zincrby("gh:user:{0}:contribution".format(key),
                                     repo_name, nevents)

                    if org is None:
                        # how connected are these two users?
                        pipe.zincrby("gh:user:{0}:connection".format(key),
                                     owner, nevents)
                        pipe.zincrby("gh:user:{0}:connection".format(okey),
                                     actor, nevents)

                        # update the global count of connections.
                        pipe.incr("gh:connection", nevents)
                        pipe.zincrby("gh:connection:user", key, nevents)
                        pipe.zincrby("gh:connection:user", okey, nevents)

                # Check for swear words.
                curses = []
                if evttype == "PushEvent":
                    for sha in event.get("payload", {}).get("shas", []):
                        words = sw_re.findall(sha[2])
                        if len(words):
                            # Save the commit hash.
                            lnk = repo_name + "/commit/" + sha[0]
                            pipe.lpush("gh:user:{0}:vcommit".format(key), lnk)

                            # Count the specific words.
                            curses += words
                            for w in words:
                                # Popularity of curse words.
                                pipe.zincrby("gh:curse", w, 1)

                                # User's favorite words.
                                pipe.zincrby("gh:user:{0}:curse".format(key),
                                             w, 1)

                                # Vulgar users?
                                pipe.zincrby("gh:curse:user", key, 1)

                # Do we know what the language of the repository is?
                language = repo.get("language")
                if language:
                    # Which are the most popular languages?
                    pipe.zincrby("gh:lang", language, nevents)

                    # Total number of pushes.
                    if evttype == "PushEvent":
                        pipe.zincrby("gh:pushes:lang", language, nevents)

                    # What are a user's favorite languages?
                    if contribution:
                        pipe.zincrby("gh:user:{0}:lang".format(key), language,
                                     nevents)

                    # Who are the most important users of a language?
                    if contribution:
                        pipe.zincrby("gh:lang:{0}:user".format(language),
                                     key, nevents)

                    # Vulgar languages.
                    if len(curses):
                        [pipe.zincrby("gh:lang:{0}:curse".format(language),
                                      w, 1) for w in curses]
                        pipe.zincrby("gh:curse:lang", language, len(curses))

        pipe.execute()

        print("Processed {0} events in {1} [{2:.2f} seconds]"
              .format(n, filename, time.time() - strt))


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: process.py /path/to/data/*.json.gz")
        sys.exit(1)

    pool = Pool(24)
    pool.map(process, sys.argv[1:])
