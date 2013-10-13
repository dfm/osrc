#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["fetch"]

import gevent
from gevent import monkey
monkey.patch_all()

import os
import shutil
import requests
from itertools import product
from tempfile import NamedTemporaryFile

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
filename = os.path.join(data_dir, "{year}-{month:02d}-{day:02d}-{n}.json.gz")

try:
    os.makedirs(data_dir)
except os.error:
    pass

url = "http://data.githubarchive.org/{year}-{month:02d}-{day:02d}-{n}.json.gz"


def fetch(**kwargs):
    # Download the remote file.
    remote = url.format(**kwargs)
    r = requests.get(remote)
    if r.status_code == requests.codes.ok:
        # Atomically write to disk.
        # http://stackoverflow.com/questions/2333872/ \
        #        atomic-writing-to-file-with-python
        f = NamedTemporaryFile("wb", delete=False)
        f.write(r.content)
        f.flush()
        os.fsync(f.fileno())
        f.close()
        shutil.move(f.name, local_fn)


if __name__ == "__main__":
    for year, month in product(range(2011, 2014), range(1, 13)):
        jobs = []
        for n, day in product(range(1, 32), range(24)):
            kwargs = {"year": year, "month": month, "day": day, "n": n}
            local_fn = filename.format(**kwargs)
            if not os.path.exists(local_fn):
                jobs.append(gevent.spawn(fetch, **kwargs))
        gevent.joinall(jobs)
        print("Finished {0}-{1}".format(year, month))
