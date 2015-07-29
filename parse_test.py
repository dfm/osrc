#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

import os
import glob
import json
import gzip

from osrc.models import db, Event
from osrc.process import process_repo, process_user, parse_datetime
from osrc import create_app
dirname = os.path.dirname(os.path.abspath(__file__))
app = create_app(os.path.join(dirname, "local.py"))


def parse_event(event):
    # Parse the standard elements.
    _process_event(event)

    # Parse any event specific elements.
    parser = event_types.get(event["type"], None)
    if parser is not None:
        parser(event["payload"])


def _process_event(event):
    user = process_user(event["actor"])
    repo = process_repo(event["repo"])
    dt = parse_datetime(event["created_at"])
    db.session.add(Event(
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


if __name__ == "__main__":
    with app.app_context():
        for fn in glob.iglob("data/*.json.gz"):
            print(fn)
            try:
                with gzip.GzipFile(fn) as f:
                    for i, line in enumerate(f):
                        parse_event(json.loads(line.decode("utf-8")))
            except:
                raise
            finally:
                db.session.commit()
