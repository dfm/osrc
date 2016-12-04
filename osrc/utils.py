# -*- coding: utf-8 -*-

import os
import re
import flask

__all__ = ["load_resource", "is_robot"]

def load_resource(
    filename,
    base=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
):
    return open(os.path.join(base, filename), "r")

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
