# -*- coding: utf-8 -*-

import flask

__all__ = ["create_app"]


def before_first_request():
    pass


def create_app(config_filename=None):
    app = flask.Flask(__name__)
    app.config.from_object("osrc.default_settings")
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    # Set up the database.
    from .models import db
    db.init_app(app)

    # Before request.
    app.before_first_request(before_first_request)

    # Bind the blueprints.
    from .api import api
    app.register_blueprint(api, url_prefix="/api")

    # Debugging.
    if app.debug:
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.config["PROFILE"] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

    return app
