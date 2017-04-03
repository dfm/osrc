# -*- coding: utf-8 -*-

import os
import re
import json
import flask

__all__ = ["load_resource", "load_json_resource", "load_text_resource",
           "is_robot"]

def load_resource(
    filename,
    base=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
    handler=lambda fh: fh.read()
):
    if "resources" not in flask.g:
        flask.g.resources = dict()
    if filename not in flask.g.resources:
        with open(os.path.join(base, filename), "r") as f:
            flask.g.resources[filename] = handler(f)
    return flask.g.resources[filename]

def load_json_resource(filename, **kwargs):
    kwargs["handler"] = json.load
    return load_resource(filename, **kwargs)

def load_text_resource(filename, **kwargs):
    return load_resource(filename, **kwargs)

def is_robot():
    """
    Adapted from: https://github.com/jpvanhal/flask-split
    """
    robot_regex = r"""
        (?i)\b(
            Baidu|
            Gigabot|
            Googlebot|
            libwww-perl|
            lwp-trivial|
            msnbot|
            bingbot|
            SiteUptime|
            Slurp|
            WordPress|
            ZIBB|
            ZyBorg|
            YandexBot
        )\b
    """
    user_agent = flask.request.headers.get("User-Agent", "")
    return re.search(robot_regex, user_agent, flags=re.VERBOSE)
