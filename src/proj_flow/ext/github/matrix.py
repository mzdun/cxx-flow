# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.ext.github.matrix** implements ``./flow github matrix``
command.
"""

import argparse
import json
import os
import sys
from typing import Annotated, Optional

from proj_flow.api import arg, env
from proj_flow.flow.configs import Configs


@arg.command("github", "matrix")
def matrix(
    official: Annotated[
        bool, arg.FlagArgument(help="Cut matrix to release builds only")
    ],
    rt: env.Runtime,
):
    """Supply data for GitHub Actions"""

    configs = Configs(
        rt,
        argparse.Namespace(configs=[], matrix=True, official=official),
        expand_compilers=False,
    )

    usable = [usable.items for usable in configs.usable]
    for config in usable:
        if "--orig-compiler" in config:
            orig_compiler = config["--orig-compiler"]
            del config["--orig-compiler"]
            config["compiler"] = orig_compiler

    if "GITHUB_ACTIONS" in os.environ:
        var = json.dumps({"include": usable})
        GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT")
        if GITHUB_OUTPUT is not None:
            with open(GITHUB_OUTPUT, "a", encoding="UTF-8") as github_output:
                print(f"matrix={var}", file=github_output)
        else:
            print(f"matrix={var}")
    else:
        json.dump(usable, sys.stdout)
