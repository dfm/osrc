#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse

try:
    import osrc  # NOQA
except ImportError:
    import sys
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
finally:
    from osrc.models import db
    from osrc import create_app

if __name__ == "__main__":
    dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_settings = os.path.join(dirname, "local.py")

    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        choices=["create", "drop"],
                        nargs="+",
                        help="create/drop the tables")
    parser.add_argument("-f", "--filename",
                        default=default_settings,
                        help="a Python file with the app settings")
    args = parser.parse_args()

    app = create_app(args.filename)
    with app.app_context():
        if "drop" in args.action:
            print("drop")
            db.drop_all()
        if "create" in args.action:
            print("create")
            db.create_all()
