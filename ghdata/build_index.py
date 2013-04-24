#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["build_index"]

import os
import numpy as np
import h5py
import redis
import pyflann

_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
evttypes = [l.strip() for l in open(os.path.join(_basepath, "evttypes.txt"))]
langs = [l.strip() for l in open(os.path.join(_basepath, "languages.txt"))]

index_filename = os.path.join(_basepath, "index.h5")
points_filename = os.path.join(_basepath, "points.h5")

nevts = len(evttypes)
nlangs = len(langs)
nvector = 1 + 7 + nevts + 1 + 1 + 1 + 1 + nlangs + 1


def build_index():
    r = redis.Redis()

    usernames = r.zrevrange("gh:user", 500, 50500)

    pipe = r.pipeline()
    for user in usernames:
        get_vector(user, pipe=pipe)

    results = pipe.execute()
    points = np.zeros([len(usernames), nvector])
    for i in range(len(usernames)):
        points[i, :] = parse_vector(results[8 * i:8 * (i + 1)])

    flann = pyflann.FLANN()
    flann.build_index(points)
    flann.save_index(index_filename)
    with h5py.File(points_filename, "w") as f:
        f["points"] = points
        f["names"] = usernames


def get_vector(user, pipe=None):
    no_pipe = False
    if pipe is None:
        r = redis.Redis()
        pipe = r.pipeline()
        no_pipe = True

    pipe.zscore("gh:user", user)
    pipe.hgetall("gh:user:{0}:day".format(user))
    pipe.zrevrange("gh:user:{0}:event".format(user), 0, -1,
                   withscores=True)
    pipe.zcard("gh:user:{0}:contribution".format(user))
    pipe.zcard("gh:user:{0}:connection".format(user))
    pipe.zcard("gh:user:{0}:repo".format(user))
    pipe.zcard("gh:user:{0}:lang".format(user))
    pipe.zrevrange("gh:user:{0}:lang".format(user), 0, -1, withscores=True)

    if no_pipe:
        return pipe.execute()


def parse_vector(results):
    points = np.zeros(nvector)
    total = int(results[0])

    points[0] = 1.0 / (total + 1)

    # Week means.
    for k, v in results[1].iteritems():
        points[1 + int(k)] = float(v) / total

    # Event types.
    n = 8
    for k, v in results[2]:
        points[n + evttypes.index(k)] = float(v) / total

    # Number of contributions, connections and languages.
    n += nevts
    points[n] = 1.0 / (float(results[3]) + 1)
    points[n + 1] = 1.0 / (float(results[4]) + 1)
    points[n + 2] = 1.0 / (float(results[5]) + 1)
    points[n + 3] = 1.0 / (float(results[6]) + 1)

    # Top languages.
    n += 4
    for k, v in results[7]:
        if k in langs:
            points[n + langs.index(k)] = float(v) / total
        else:
            # Unknown language.
            points[-1] = float(v) / total

    return points


def get_neighbors(name):
    # Get the vector for this user.
    vector = parse_vector(get_vector(name))

    # Load the points and user names.
    with h5py.File(points_filename, "r") as f:
        points = f["points"][...]
        usernames = f["names"][...]

    # Load the index.
    flann = pyflann.FLANN()
    flann.load_index(index_filename, points)

    # Find the neighbors.
    inds, dists = flann.nn_index(vector, num_neighbors=6)
    inds = inds[0]
    if usernames[inds[0]] == name:
        inds = inds[1:]
    else:
        inds = inds[:-1]

    return usernames[inds]

if __name__ == "__main__":
    build_index()
    print(get_neighbors("dfm"))
