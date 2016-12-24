#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_script import Manager

from osrc import create_app
from osrc.manage import (
    CreateTablesCommand, DropTablesCommand, UpdateCommand,
)

if __name__ == "__main__":
    manager = Manager(create_app)
    manager.add_option("-f", "--filename", dest="config_filename",
                       required=False)

    manager.add_command("create", CreateTablesCommand())
    manager.add_command("drop", DropTablesCommand())
    manager.add_command("update", UpdateCommand())

    manager.run()
