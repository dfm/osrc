#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from osrc import create_app

if __name__ == "__main__":
    dirname = os.path.dirname(os.path.abspath(__file__))
    app = create_app(os.path.join(dirname, "local.py"))
    app.debug = True
    app.run()
