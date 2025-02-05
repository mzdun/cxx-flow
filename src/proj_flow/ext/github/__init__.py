# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.ext.github** add the ``github`` command, replacing the old
``ci`` code.
"""

from proj_flow.api import arg

from . import matrix, release

__all__ = ["matrix", "release"]


@arg.command("github")
def main():
    """Interact with GitHub workflows and releases"""
