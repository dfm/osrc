# -*- coding: utf-8 -*-

import os

__all__ = ["load_resource"]

def load_resource(
    filename,
    base=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
):
    return open(os.path.join(base, filename), "r")
