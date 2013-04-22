#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = []

import os
import json
import numpy as np
import redis
import pyflann

redis_pool = redis.ConnectionPool()

_basepath = os.path.dirname(os.path.abspath(__file__))
evttypes = [l.strip() for l in open(os.path.join(_basepath, "evttypes.txt"))]
nevts = len(evttypes)
ndays = 7

nvector = nevts + ndays + 2


def days_means():
    r = redis.Redis(connection_pool=redis_pool)
    usernames = r.zrevrange("gh:users", 500, 5500)
    data = np.array([get_days(u) for u in usernames])
    flann = pyflann.FLANN()
    mu = flann.kmeans(data, 12)
    return [list(m) for m in mu]


def get_days(username):
    r = redis.Redis(connection_pool=redis_pool)
    pipe = r.pipeline(transaction=False)
    pipe.zscore("gh:users", username)
    pipe.zrange("gh:days:{0}".format(username), 0, 7, withscores=True)
    results = pipe.execute()

    total = float(results[0])
    vector = np.zeros(ndays)
    for day in results[1]:
        vector[int(day[0])] = float(day[1])
    return vector / total


def get_vector(username):
    vector = np.zeros(nvector)
    r = redis.Redis(connection_pool=redis_pool)
    pipe = r.pipeline(transaction=False)
    pipe.zscore("gh:users", username)
    pipe.zrange("gh:days:{0}".format(username), 0, 7, withscores=True)
    pipe.zrange("gh:events:{0}".format(username), 0, 20, withscores=True)
    pipe.zcard("gh:repos:{0}".format(username))
    pipe.zcard("gh:langs:{0}".format(username))
    results = pipe.execute()

    total = float(results[0])

    for day in results[1]:
        vector[int(day[0])] = float(day[1])

    for evt in results[2]:
        vector[ndays + evttypes.index(evt[0])] = float(evt[1])

    vector /= total

    vector[ndays + nevts] = float(results[3])
    vector[ndays + nevts + 1] = float(results[4])

    return vector


def from_vector(vector):
    result = {}
    result["days"] = list(vector[:ndays])
    result["events"] = dict(zip(evttypes, vector[ndays:ndays + nevts]))
    result["repos"] = vector[ndays + nevts]
    result["langs"] = vector[ndays + nevts + 1]
    return result


if __name__ == "__main__":
    json.dump(days_means(), open("www/data/days_means.json", "w"))
