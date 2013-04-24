#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="ghdata",
    packages=["ghdata"],
    package_data={"ghdata": ["templates/*"]},
    include_package_data=True,
)
