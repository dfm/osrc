#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from osrc.models import db
from osrc import create_app
dirname = os.path.dirname(os.path.abspath(__file__))
app = create_app(os.path.join(dirname, "local.py"))

if __name__ == "__main__":
    with app.app_context():
        if "drop" in sys.argv:
            db.drop_all()
        elif "create" in sys.argv:
            db.create_all()
        else:
            print("Usage: create or drop")
