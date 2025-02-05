# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.minimal** defines minimal extension package: ``bootstrap``
and ``run`` commands, with basic set of steps.
"""

from proj_flow.api import arg

from . import bootstrap

__all__ = ["bootstrap"]
