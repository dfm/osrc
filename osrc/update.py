# -*- coding: utf-8 -*-

import time
import json
import gzip
import requests
from io import BytesIO
from datetime import date, timedelta

from .models import db, Event
from .process import process_repo, process_user, parse_datetime


# The URL template for the GitHub Archive.
archive_url = ("http://data.githubarchive.org/"
               "{year}-{month:02d}-{day:02d}-{n}.json.gz")


def process_one(fh):
    strt = time.time()
    count = 0
    with gzip.GzipFile(fileobj=BytesIO(fh)) as f:
        for line in f:
            parse_event(json.loads(line.decode("utf-8")))
            count += 1
    db.session.commit()
    print("... processed {0} events in {1} seconds"
          .format(count, time.time() - strt))


def parse_event(event):
    # Parse the standard elements.
    _process_event(event)

    # Parse any event specific elements.
    parser = event_types.get(event["type"], None)
    if parser is not None:
        parser(event["payload"])


def _process_event(event):
    q = Event.query.filter(Event.id == event["id"])
    if q.first() is not None:
        return
    user = process_user(event["actor"])
    repo = process_repo(event["repo"])
    dt = parse_datetime(event["created_at"])
    db.session.add(Event(
        id=event["id"],
        event_type=event["type"],
        datetime=dt,
        day=dt.weekday(),
        hour=dt.hour,
        user=user,
        repo=repo,
    ))


def _process_fork(payload):
    process_repo(payload["forkee"])


def _process_pull_request(payload):
    process_repo(payload["pull_request"]["base"]["repo"])


def _process_pull_request_comment(payload):
    _process_pull_request(payload)


event_types = dict(
    ForkEvent=_process_fork,
    PullRequestEvent=_process_pull_request,
    PullRequestReviewCommentEvent=_process_pull_request_comment,
)


def update(files=None, since=None):
    try:
        if files is not None:
            for fn in files:
                print("Processing: {0}".format(fn))
                process_one(open(fn, "rb"))
        else:
            today = date.today()
            if since is None:
                since = today - timedelta(1)
            else:
                since = date(**dict(zip(["year", "month", "day"],
                                    map(int, since.split("-")))))

            print("Updating since '{0}'".format(since))

            while since < today:
                base_date = dict(
                    year=since.year,
                    month=since.month,
                    day=since.day,
                )
                # for n in range(24):
                for n in range(1):
                    url = archive_url.format(**(dict(base_date, n=n)))
                    print("Processing: {0}".format(url))
                    r = requests.get(url)
                    r.raise_for_status()
                    process_one(r.content)
                    db.session.commit()

                since += timedelta(1)

    except:
        raise

    finally:
        db.session.commit()
