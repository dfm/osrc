#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="osrc",
    version="2.0.0",
    author="Daniel Foreman-Mackey",
    author_email="danfm@nyu.edu",
    url="http://osrc.dfm.io",
    packages=["osrc"],
    package_data={"osrc": ["*.json", "templates/*", "static/*"]},
    include_package_data=True,
)
