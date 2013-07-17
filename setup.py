#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="osrc",
    packages=["osrc"],
    package_data={"osrc": ["templates/*", "static/*"]},
    include_package_data=True,
)
