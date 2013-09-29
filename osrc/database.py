#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["redis_pool", "format_key"]

import flask
import redis
redis_pool = None


def get_pipeline():
    global redis_pool
    if redis_pool is None:
        port = int(flask.current_app.config["REDIS_PORT"])
        redis_pool = redis.ConnectionPool(port=port)
    r = redis.Redis(connection_pool=redis_pool)
    return r.pipeline()


def format_key(key):
    return "{0}:{1}".format(flask.current_app.config["REDIS_PREFIX"], key)
