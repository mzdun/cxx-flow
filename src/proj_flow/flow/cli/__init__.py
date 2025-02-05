# PYTHON_ARGCOMPLETE_OK

# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.flow.cli** provides command-line entry for the *Project Flow*.
"""

import argparse
import os
import sys
from typing import Dict, List, cast

from proj_flow import __version__
from proj_flow.api import env
from proj_flow.flow import steps
from proj_flow.flow.cli import cmds, finder


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


def _expand_shortcuts(parser: argparse.ArgumentParser, args: argparse.Namespace):
    args_kwargs = dict(args._get_kwargs())
    shortcuts: Dict[str, List[str]] = parser.shortcuts  # type: ignore
    for key in shortcuts:
        try:
            if not args_kwargs[key]:
                continue
            cast(List[str], args.configs).extend(shortcuts[key])
            break
        except KeyError:
            continue


def __main():
    _change_dir()

    flow_cfg = env.FlowConfig(root=finder.autocomplete.find_project())
    steps.clean_aliases(flow_cfg)

    parser = cmds.build_argparser(flow_cfg)
    finder.autocomplete(parser)
    args = parser.parse_args()
    _expand_shortcuts(parser, args)

    sys.exit(cmds.BuiltinEntry.run_entry(args, flow_cfg))


def main():
    """Entry point for *Project Flow* tool."""
    try:
        __main()
    except KeyboardInterrupt:
        sys.exit(1)
