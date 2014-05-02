#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import logging
from itertools import imap
from osrc.database import get_pipeline, format_key

# The default time-to-live for every key.
DEFAULT_TTL = 2 * 7 * 24 * 60 * 60
TEMP_TTL = 24 * 60 * 60


def set_expire():
    pipe = get_pipeline()

    # Get the list of all keys.
    keys = pipe.keys().execute()[0]
    n = float(len(keys))
    print("Found {0:.0f} keys".format(n))

    # Loop over the keys and deal with each one.
    for i, key in enumerate(keys):
        # Skip the opt-out keys.
        if key.endswith(":optout"):
            continue

        # Deal with temporary keys.
        if any(imap(key.endswith, [":name", ":etag", ":gravatar", ":tz"])):
            pipe.expire(key, TEMP_TTL)
            continue

        # Everything else should get the default TTL.
        pipe.expire(key, DEFAULT_TTL)

        # Execute the updates in batches.
        if (i+1) % 5000 == 0:
            print("Finished {0} keys [{1:.2f} %]".format(i+1, (i+1)/n*100))
            pipe.execute()

    pipe.execute()


def del_connections():
    pipe = get_pipeline()

    # Get the list of all keys.
    keys = pipe.keys(format_key("social:connection:*")).execute()[0]
    n = float(len(keys))
    print("Found {0:.0f} keys".format(n))

    # Loop over the keys and deal with each one.
    for i, key in enumerate(keys):
        pipe.delete(key)

    pipe.execute()


if __name__ == "__main__":
    import argparse
    from osrc import create_app

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description="Add expiry dates to everything")
    parser.add_argument("--config", default=None,
                        help="The path to the local configuration file.")
    parser.add_argument("--log", default=None,
                        help="The path to the log file.")
    parser.add_argument("--connections", action="store_true",
                        help="Delete the connections?")
    args = parser.parse_args()

    largs = dict(level=logging.INFO,
                 format="[%(asctime)s] %(name)s:%(levelname)s:%(message)s")
    if args.log is not None:
        largs["filename"] = args.log
    logging.basicConfig(**largs)

    # Initialize a flask app.
    app = create_app(args.config)

    # Set up the app in a request context.
    with app.test_request_context():
        if args.connections:
            del_connections()
        else:
            set_expire()
