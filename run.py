#!/usr/bin/env python
# -*- coding: utf-8 -*-

from osrc import create_app

if __name__ == "__main__":
    app = create_app()
    app.debug = True
    app.run()
