#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_connection", "get_pipeline", "format_key"]

import flask
import redis
redis_pool = None


def get_connection():
    global redis_pool
    if redis_pool is None:
        port = int(flask.current_app.config["REDIS_PORT"])
        redis_pool = redis.ConnectionPool(port=port)
    return redis.Redis(connection_pool=redis_pool)


def get_pipeline():
    r = get_connection()
    return r.pipeline()


def format_key(key):
    return "{0}:{1}".format(flask.current_app.config["REDIS_PREFIX"], key)
