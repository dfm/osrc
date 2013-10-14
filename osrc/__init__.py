#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["create_app"]

import flask


def create_app(config_filename=None):
    app = flask.Flask(__name__)
    app.config.from_object("osrc.default_settings")
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    from .frontend import frontend, firstname, compare
    app.register_blueprint(frontend)
    app.jinja_env.filters["firstname"] = firstname
    app.jinja_env.filters["compare"] = compare
    return app
