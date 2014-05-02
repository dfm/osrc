#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["create_app"]

import flask


def internal_error(error):
    return flask.render_template("error.html"), 500


def not_found(error):
    return flask.render_template("noinfo.html"), 404


def down():
    return flask.render_template("down.html")


def create_app(config_filename=None):
    app = flask.Flask(__name__)
    app.config.from_object("osrc.default_settings")
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    # Add some custom error handlers.
    app.error_handler_spec[None][404] = not_found
    app.error_handler_spec[None][500] = internal_error

    # FIXME: this is how we do downtime?!?
    # app.add_url_rule("/", "down", down)

    from .frontend import frontend, firstname, compare
    app.register_blueprint(frontend)
    app.jinja_env.filters["firstname"] = firstname
    app.jinja_env.filters["compare"] = compare

    return app
