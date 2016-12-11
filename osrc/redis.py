# -*- coding: utf-8 -*-

from __future__ import division, print_function

import flask
import redis

__all__ = ["get_connection", "get_pipeline", "format_key"]

redis_pool = None

def get_connection():
    global redis_pool
    if redis_pool is None:
        url = flask.current_app.config["REDIS_URI"]
        redis_pool = redis.ConnectionPool().from_url(url)
    return redis.StrictRedis(connection_pool=redis_pool)

def get_pipeline():
    r = get_connection()
    return r.pipeline()

def format_key(key):
    return "{0}:{1}".format(flask.current_app.config["REDIS_PREFIX"], key)
