# -*- coding: utf-8 -*-

import os
import flask

__all__ = ["create_app"]


def before_first_request():
    pass


def create_app(config_filename=None):
    app = flask.Flask(__name__)
    app.config.from_object("osrc.default_settings")
    if "OSRC_SETTINGS" in os.environ:
        app.config.from_envvar("OSRC_SETTINGS")
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    # Rate limiting
    from .rate_limit import limiter
    limiter.init_app(app)

    # Set up the database.
    from .models import db
    db.init_app(app)

    # Before request.
    app.before_first_request(before_first_request)

    # Bind the blueprints.
    from .api import api
    app.register_blueprint(api, url_prefix="/api")

    from .frontend import frontend
    app.register_blueprint(frontend)

    # Debugging.
    if app.debug:
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.config["PROFILE"] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

    return app
