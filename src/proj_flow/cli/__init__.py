# PYTHON_ARGCOMPLETE_OK

# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.cli** provides command-line entry for the *Project Flow*.
"""

import argparse
import os
import sys
from pprint import pprint
from typing import Dict, Optional, Tuple

from proj_flow.api import arg, env
from proj_flow.flow.cli import finder


def main():
    """Entry point for *Project Flow* tool."""
    try:
        __main()
    except KeyboardInterrupt:
        sys.exit(1)


def _change_dir():
    root = argparse.ArgumentParser(
        prog="proj-flow",
        usage="proj-flow [-h] [--version] [-C [dir]] {command} ...",
        add_help=False,
    )
    root.add_argument("-C", dest="cd", nargs="?")

    args, _ = root.parse_known_args()
    if args.cd:
        os.chdir(args.cd)


def _simple(menu: arg._Command) -> Tuple[Optional[str], Dict[str, tuple]]:
    return (menu.doc, {key: _simple(value) for key, value in menu.subs.items()})


def __main():
    _change_dir()

    flow_cfg = env.FlowConfig(root=finder.autocomplete.find_project())
    pprint(flow_cfg.root)
    pprint(flow_cfg._cfg)
    pprint(_simple(arg.get_commands())[1])

    sys.exit(0)
