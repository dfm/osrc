# -*- coding: utf-8 -*-

__all__ = [
    "CreateTablesCommand", "DropTablesCommand", "UpdateCommand",
]

from flask.ext.script import Command, Option

from .models import db
from .update import update


class CreateTablesCommand(Command):
    def run(self):
        db.create_all()


class DropTablesCommand(Command):
    def run(self):
        db.drop_all()


class UpdateCommand(Command):

    option_list = (
        Option("-s", "--since", dest="since", required=False),
    )

    def run(self, since):
        update(since=since)
