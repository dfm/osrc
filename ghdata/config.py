#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os

DEBUG = False
TESTING = False
SECRET_KEY = os.environ["SECRET_KEY"]
LOG_FILENAME = os.environ["LOG_FILENAME"]
print(LOG_FILENAME)

# GitHub API.
GITHUB_ID = os.environ["GITHUB_ID"]
GITHUB_SECRET = os.environ["GITHUB_SECRET"]
