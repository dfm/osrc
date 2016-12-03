# -*- coding: utf-8 -*-

import glob

from flask.ext.script import Command, Option

from .models import db
from .update import update
from .redis import get_connection

__all__ = [
    "CreateTablesCommand", "DropTablesCommand", "UpdateCommand",
]


class CreateTablesCommand(Command):
    def run(self):
        db.create_all()


class DropTablesCommand(Command):
    def run(self):
        db.drop_all()
        get_connection().flushdb()


class UpdateCommand(Command):

    option_list = (
        Option("-s", "--since", dest="since", required=False),
        Option("-p", "--pattern", dest="pattern", required=False),
    )

    def run(self, since, pattern):
        files = None
        if pattern is not None:
            files = glob.glob(pattern)
        update(files=files, since=since)
