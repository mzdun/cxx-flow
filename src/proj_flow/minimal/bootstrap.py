# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.plugins.commands.bootstrap** implements ``./flow bootstrap`` command.
"""

import os

from proj_flow.api import arg


@arg.command("bootstrap")
def main():
    """Finish bootstrapping on behalf of flow.py"""

    GITHUB_ENV = os.environ.get("GITHUB_ENV")
    if GITHUB_ENV is not None:
        with open(GITHUB_ENV, "a", encoding="UTF-8") as github_env:
            PATH = os.environ["PATH"]
            print(f"PATH={PATH}", file=github_env)
