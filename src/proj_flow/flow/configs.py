# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.flow.configs** provides :class:`Configs`, which uses
:class:`api.env.FlowConfig` to load the matrix definition and filter it out
using ``-D`` switches.
"""


import argparse
import os
from typing import Any, Callable, Dict, List

from proj_flow.api import env
from proj_flow.base import matrix


def _compiler_inner(
    value: str,
    used_compilers: Dict[str, List[List[str]]],
    config_names: Dict[str, List[str]],
):
    compiler, names = matrix.find_compiler(value, config_names)
    if compiler not in used_compilers:
        used_compilers[compiler] = []
    used_compilers[compiler].append(names)
    return compiler


def _compiler(
    used_compilers: Dict[str, List[List[str]]], config_names: Dict[str, List[str]]
):
    return lambda value: _compiler_inner(value, used_compilers, config_names)


def _boolean_inner(value: str, with_name: str):
    v = value.lower()
    return v in _TRUE or v == with_name


def _boolean(with_name: str):
    return lambda value: _boolean_inner(value, with_name)


_TRUE = {"true", "on", "yes", "1"}
_boolean_sanitizer = _boolean("with-sanitizer")


def _types(
    used_compilers: Dict[str, List[List[str]]], config_names: Dict[str, List[str]]
):
    return {
        "compiler": _compiler(used_compilers, config_names),
        "sanitizer": _boolean_sanitizer,
    }


def _config(config: List[str], only_host: bool, types: Dict[str, Callable[[str], Any]]):
    args = {}
    for arg in config:
        if arg[:1] == "-":
            continue
        _arg = arg.split("=", 1)
        if len(_arg) == 1:
            continue

        name, vals = _arg
        name = name.strip()
        conv = types.get(name, lambda value: value)
        values = {conv(val.strip()) for val in vals.split(",")}
        if name in args:
            values.update(args[name])
        args[name] = list(values)

    if only_host and "os" not in args:
        args["os"] = [env.platform]

    return args


def _expand_one(config: dict, github_os: str, os_in_name: str):
    os_ver = github_os.split("-")[1]
    build_name = f"{config['build_type']} with {config['compiler']} on {os_in_name}"
    if config["sanitizer"]:
        build_name += " (and sanitizer)"
    config["github_os"] = github_os
    config["build_name"] = build_name
    config["needs_gcc_ppa"] = os_ver != "latest" and config["os"] == "ubuntu"
    return config


def _expand_config(config: dict, spread_lts: bool, lts_list: Dict[str, List[str]]):
    if spread_lts:
        spread = lts_list.get(config["os"], [])
        if len(spread):
            return [
                _expand_one({key: config[key] for key in config}, lts, lts)
                for lts in spread
            ]
    return [_expand_one(config, f"{config['os']}-latest", config["os"])]


def _load_flow_data(rt: env.Runtime):
    root = ".flow"
    paths = [os.path.join(root, "matrix.yml")]
    if rt.official:
        paths.append(os.path.join(root, "official.yml"))
    configs, keys = matrix.load_matrix(*paths)

    if rt.no_coverage:
        for conf in configs:
            if "coverage" in conf:
                del conf["coverage"]

    return configs, keys


class Configs:
    usable: List[env.Config] = []

    def __init__(
        self, rt: env.Runtime, args: argparse.Namespace, expand_compilers=True
    ):
        super()
        configs, keys = _load_flow_data(rt)

        used_compilers: Dict[str, List[List[str]]] = {}

        types = _types(used_compilers=used_compilers, config_names=rt.compiler_names)
        arg_configs = matrix.cartesian(_config(args.configs, rt.only_host, types))

        # from commands/github
        spread_lts = hasattr(args, "matrix") and not not args.matrix

        turned = matrix.flatten(
            [
                _expand_config(config, spread_lts, rt.lts_list)
                for config in configs
                if len(arg_configs) == 0 or matrix.matches_any(config, arg_configs)
            ]
        )

        postproc_exclude = rt.postproc_exclude
        usable = [
            config
            for config in turned
            if len(postproc_exclude) == 0
            or not matrix.matches_any(config, postproc_exclude)
        ]

        if not expand_compilers:
            self.usable = [env.Config(conf, keys) for conf in usable]
            return

        self.usable = []
        for conf in usable:
            try:
                compilers = used_compilers[conf["compiler"]]
            except KeyError:
                fallback_compiler = matrix.find_compiler(
                    conf["compiler"], config_names=rt.compiler_names
                )
                compilers = [fallback_compiler[1]]
            for compiler in compilers:
                self.usable.append(
                    env.Config(
                        {
                            **conf,
                            "compiler": compiler,
                            "--orig-compiler": conf["compiler"],
                        },
                        keys,
                    )
                )
