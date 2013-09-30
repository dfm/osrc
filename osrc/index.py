#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["rebuild_index", "get_neighbors"]

import os
import h5py
import flask
import shutil
import pyflann
import numpy as np

from .database import get_pipeline, format_key

_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
evttypes = [l.strip() for l in open(os.path.join(_basepath, "evttypes.txt"))]
langs = [l.strip() for l in open(os.path.join(_basepath, "languages.txt"))]

index_filename = "index.h5"
points_filename = "points.h5"

nevts = len(evttypes)
nlangs = len(langs)
nvector = 1 + 7 + nevts + 1 + 1 + 1 + 1 + nlangs + 1


def get_vector(user, pipe=None):
    """
    Given a username, fetch all of the data needed to build a behavior vector
    from the database.

    :param user: The GitHub username.
    :param pipe: (optional) if provided, simply add the requests to the
                 existing redis pipeline and don't execute the request.

    """
    no_pipe = False
    if pipe is None:
        pipe = get_pipeline()
        no_pipe = True

    user = user.lower()
    pipe.zscore(format_key("user"), user)
    pipe.hgetall(format_key("user:{0}:day".format(user)))
    pipe.zrevrange(format_key("user:{0}:event".format(user)), 0, -1,
                   withscores=True)
    pipe.zcard(format_key("user:{0}:contribution".format(user)))
    pipe.zcard(format_key("user:{0}:connection".format(user)))
    pipe.zcard(format_key("user:{0}:repo".format(user)))
    pipe.zcard(format_key("user:{0}:lang".format(user)))
    pipe.zrevrange(format_key("user:{0}:lang".format(user)), 0, -1,
                   withscores=True)

    if no_pipe:
        return pipe.execute()


def parse_vector(results):
    """
    Parse the results of a call to ``get_vector`` into a numpy array.

    :param results: The list of results from the redis request.

    """
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


def _h5_filename(fn):
    return os.path.join(flask.current_app.config.get("INDEX_DIR", ""), fn)


def get_neighbors(name, num=5):
    """
    Find the K nearest neighbors to a user in "behavior space".

    :param name: The GitHub username.
    :param num: (optioanl; default: 5) The number of neighbors to find.

    """
    # Get the vector for this user.
    vector = parse_vector(get_vector(name))

    # Load the points and user names.
    with h5py.File(_h5_filename(points_filename), "r") as f:
        points = f["points"][...]
        usernames = f["names"][...]

    # Load the index.
    flann = pyflann.FLANN()
    flann.load_index(_h5_filename(index_filename), points)

    # Find the neighbors.
    inds, dists = flann.nn_index(vector, num_neighbors=num+1)
    inds = inds[0]
    if usernames[inds[0]] == name:
        inds = inds[1:]
    else:
        inds = inds[:-1]

    usernames = usernames[inds]

    return list(usernames)


def rebuild_index():
    """
    Rebuild the K-nearest neighbors index based on 50000 of the most active
    users (ignoring the top 500 most active).

    """
    pipe = get_pipeline()
    usernames = pipe.zrevrange(format_key("user"), 500, 50500).execute()[0]

    for user in usernames:
        get_vector(user, pipe=pipe)

    results = pipe.execute()
    points = np.zeros([len(usernames), nvector])
    for i in range(len(usernames)):
        points[i, :] = parse_vector(results[8 * i:8 * (i + 1)])

    flann = pyflann.FLANN()
    flann.build_index(points)

    # Save the index.
    fn1 = _h5_filename(index_filename)
    tmp1 = fn1 + ".tmp"
    flann.save_index(tmp1)

    # Save the index coordinates.
    fn2 = _h5_filename(points_filename)
    tmp2 = fn2 + ".tmp"
    with h5py.File(tmp2, "w") as f:
        f["points"] = points
        f["names"] = usernames

    # Atomically move the index files into place.
    shutil.move(tmp1, fn1)
    shutil.move(tmp2, fn2)
