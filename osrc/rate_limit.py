# -*- coding: utf-8 -*-

from __future__ import division, print_function
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

__all__ = ["limiter"]

limiter = Limiter(
    key_func=get_remote_address,
    global_limits=["10/minute"],
)
