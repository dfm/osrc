#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["fetch"]

import gevent
from gevent import monkey
monkey.patch_all()

import os
import requests
from itertools import product

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
filename = os.path.join(data_dir, "{year}-{month:02d}-{day:02d}-{n}.json.gz")

try:
    os.makedirs(data_dir)
except os.error:
    pass

url = "http://data.githubarchive.org/{year}-{month:02d}-{day:02d}-{n}.json.gz"


def fetch(year, month, day, n):
    kwargs = {"year": year, "month": month, "day": day, "n": n}
    remote = url.format(**kwargs)
    r = requests.get(remote)
    if r.status_code == requests.codes.ok:
        local_fn = filename.format(**kwargs)
        with open(local_fn, "wb") as f:
            f.write(r.content)
        print("Saved: {0}".format(local_fn))

    else:
        print("Skipped: {0}".format(remote))


if __name__ == "__main__":
    year = 2013
    for month, day in product(range(1, 4), range(1, 32)):
        jobs = [gevent.spawn(fetch, year, month, day, n) for n in range(24)]
        gevent.joinall(jobs)
        print("Finished {0}-{1}-{2}".format(year, month, day))
