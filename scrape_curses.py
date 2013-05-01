#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import requests
from bs4 import BeautifulSoup

url = "http://www.noswearing.com/dictionary/{0}"


def get_letter(letter):
    r = requests.get(url.format(letter))
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    tree = BeautifulSoup(r.text)

    return [el.text
            for el in tree.find("table", width="650").find_all("b")][:-1]


if __name__ == "__main__":
    fn = "ghdata/static/swears.txt"
    open(fn, "w").close()
    for l in "abcdefghijklmnopqrstuvwxyz":
        print("Getting words for letter: '{0}'...".format(l), end="")
        words = get_letter(l)
        print(" found {0}".format(len(words)))
        if len(words):
            with open(fn, "a") as f:
                f.write("\n".join(words) + "\n")
