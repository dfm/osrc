#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["week_means"]

import json
import numpy as np
import redis
import pyflann


def week_means():
    r = redis.Redis()

    usernames = r.zrevrange("gh:user", 500, 10500)
    pipe = r.pipeline()

    for user in usernames:
        pipe.zscore("gh:user", user)
        pipe.hgetall("gh:user:{0}:day".format(user))

    results = pipe.execute()
    points = np.zeros([len(usernames), 7])
    for i in range(len(usernames)):
        total = int(results[2 * i])
        for k, v in results[2 * i + 1].iteritems():
            points[i, int(k)] = float(v) / total

    flann = pyflann.FLANN()
    mu = flann.kmeans(points, 12)
    return [list(m) for m in mu]


if __name__ == "__main__":
    import os
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static",
                      "week_means_tmp.json")
    json.dump(week_means(), open(fn, "w"))
