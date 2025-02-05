# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.api.env** provides interaction with project environment:

- :class:`FlowConfig` loads the project config in ``.flow/config.yml``.
- :class:`Runtime` provides means to run tools and print messages, while
  respecting ``--dry-run``, ``--silent`` and ``--verbose``.
- :class:`Config` represents single run configuration.
"""

import argparse
import importlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, cast

import yaml

from proj_flow.base import plugins, uname
from proj_flow.base.plugins import load_module_plugins

platform = uname.uname()[0]


_flow_config_default_compiler: Optional[Dict[str, str]] = None


def default_compiler():
    try:
        return os.environ["DEV_CXX"]
    except KeyError:
        pass

    flow_config_default_compiler = _flow_config_default_compiler or {}

    try:
        return flow_config_default_compiler[platform]
    except KeyError:
        print(
            f"-- KeyError: {platform} in {flow_config_default_compiler}",
            file=sys.stderr,
        )
        return "?"
    except TypeError:
        print(f"-- TypeError: internal: flow config not ready yet", file=sys.stderr)
        return "?"


class Printer:
    @staticmethod
    def hide(arg: str, secrets: List[str]):
        for secret in secrets:
            arg = arg.replace(secret, "?" * max(15, len(secret)))
        return arg

    @staticmethod
    def print_arg(arg: str, secrets: List[str], raw: bool):
        color = ""
        arg = Printer.hide(arg, secrets)
        if arg[:1] == "-":
            color = "\033[2;37m"
        if not raw:
            arg = shlex.join([arg])
        if color == "" and arg[:1] in ["'", '"']:
            color = "\033[2;34m"
        if color == "":
            return arg
        return f"{color}{arg}\033[m"

    @staticmethod
    def print_cmd(*args: str, use_color: bool = True, secrets: List[str], raw: bool):
        cmd = args[0] if raw else shlex.join([args[0]])
        if not use_color:
            if raw:
                print(
                    cmd,
                    *(Printer.hide(arg, secrets) for arg in args[1:]),
                    file=sys.stderr,
                )
            else:
                print(
                    cmd,
                    shlex.join(Printer.hide(arg, secrets) for arg in args[1:]),
                    file=sys.stderr,
                )
            return

        printed = " ".join([Printer.print_arg(arg, secrets, raw) for arg in args[1:]])
        print(f"\033[33m{cmd}\033[m {printed}", file=sys.stderr)


@dataclass
class RunAlias:
    name: str
    doc: str
    steps: List[str]

    @staticmethod
    def from_json(name: str, alias: Union[dict, list]):
        if isinstance(alias, dict):
            doc: str = alias.get("doc", "")
            steps: List[str] = alias.get("steps", [])
        else:
            doc = ""
            steps = alias
        if not doc:
            doc = f'Shortcut for "run -s {",".join(steps)}"'

        return RunAlias(name, doc, steps)


class FlowConfig:
    _cfg: dict
    steps: list = []
    aliases: List[RunAlias] = []
    root: str

    def __init__(self, cfg: Optional["FlowConfig"] = None, root: str = "."):
        if cfg is not None:
            self._cfg = cfg._cfg
            self.steps = cfg.steps
            self.aliases = cfg.aliases
            self.root = cfg.root
        else:
            self.root = os.path.abspath(root)
            self._cfg = plugins.load_data(
                os.path.join(self.root, ".flow", "config.json")
            )

            self._propagate_compilers()
            self._load_extensions()

    def _propagate_compilers(self):
        global _flow_config_default_compiler
        _flow_config_default_compiler = self.compiler_os_default

    def _load_extensions(self):
        extensions = cast(List[str], self._cfg.get("extensions", []))
        extensions.insert(0, "proj_flow.minimal")

        local_extensions = os.path.abspath(
            os.path.join(self.root, ".flow", "extensions")
        )
        if os.path.isdir(local_extensions):
            sys.path.insert(0, local_extensions)

        for extension in extensions:
            importlib.import_module(extension)

    def _load_plugins(self):
        std_plugins = importlib.import_module("proj_flow.plugins")
        load_module_plugins(std_plugins)

        local_plugins = os.path.abspath(os.path.join(self.root, ".flow", "extensions"))
        if not os.path.exists(local_plugins):
            return

        if not os.path.isdir(local_plugins):
            plugins = importlib.import_module(local_plugins)
            load_module_plugins(plugins, can_fail=True)
            return

        sys.path.insert(0, local_plugins)

        for root, dirnames, _ in os.walk(local_plugins):
            for dirname in dirnames:
                init = os.path.join(root, dirname, "__init__.py")
                if not os.path.isfile(init):
                    continue
                plugins = importlib.import_module(dirname)
                load_module_plugins(plugins, can_fail=True)
            dirnames[:] = []

        sys.path.pop(0)

    @property
    def entry(self) -> Dict[str, dict]:
        return self._cfg.get("entry", {})

    @property
    def compiler(self) -> Dict[str, dict]:
        return self._cfg.get("compiler", {})

    @property
    def compiler_names(self) -> Dict[str, List[str]]:
        return self.compiler.get("names", {})

    @property
    def compiler_os_default(self) -> Dict[str, str]:
        return self.compiler.get("os-default", {})

    @property
    def lts_list(self) -> Dict[str, List[str]]:
        return self._cfg.get("lts", {})

    @property
    def postproc(self) -> dict:
        return self._cfg.get("postproc", {})

    @property
    def postproc_exclude(self) -> List[dict]:
        return self.postproc.get("exclude", [])

    @property
    def shortcuts(self) -> Dict[str, dict]:
        return self._cfg.get("shortcuts", {})


def _mkdir(dirname: str):
    os.makedirs(dirname, exist_ok=True)


def _ls(dirname: str, shallow=True):
    result = []
    for root, dirnames, filenames in os.walk(dirname):
        if shallow:
            dirnames[:] = []

        result.extend(
            os.path.relpath(os.path.join(root, filename), start=dirname)
            for filename in filenames
        )
    return result


def _cp(src: str, dst: str) -> int:
    try:
        dst = os.path.abspath(dst)
        if os.path.isdir(src):
            _mkdir(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)
        else:
            if not os.path.isdir(dst):
                _mkdir(os.path.dirname(dst))
            shutil.copy(src, dst, follow_symlinks=False)
        return 0
    except FileNotFoundError as err:
        print(err, file=sys.stderr)
        return 1


class Msg(Enum):
    """Message level for Runtime.message"""

    DEBUG = 0
    """Print only, when verbose is set"""

    STATUS = 2
    """Print when silent if not set"""

    ALWAYS = 3
    """Print always"""


MSG_GUARD: Dict[Msg, Callable[["Runtime"], bool]] = {
    Msg.DEBUG: lambda rt: rt.verbose,
    Msg.STATUS: lambda rt: not rt.silent,
    Msg.ALWAYS: lambda rt: True,
}


class Runtime(FlowConfig):
    dry_run: bool
    silent: bool
    verbose: bool
    official: bool
    no_coverage: bool
    use_color: bool
    only_host: bool
    platform: str
    secrets: List[str] = []

    def __init__(
        self, argsOrRuntime: Union[argparse.Namespace, "Runtime"], cfg: FlowConfig
    ):
        super().__init__(cfg=cfg)

        if isinstance(argsOrRuntime, argparse.Namespace):
            args = argsOrRuntime
            self.dry_run = getattr(args, "dry_run", False)
            self.silent = getattr(args, "silent", False)
            self.verbose = getattr(args, "verbose", False)
            self.official = getattr(args, "official", False)
            self.use_color = True
            self.no_coverage = False
            self.platform = platform

            if "NO_COVERAGE" in os.environ:
                self.no_coverage = True

            if "RELEASE" in os.environ and "GITHUB_ACTIONS" in os.environ:
                self.official = not not json.loads(os.environ["RELEASE"])

            self.only_host = not (self.dry_run or self.official)
        else:
            rt = argsOrRuntime
            self.dry_run = rt.dry_run
            self.silent = rt.silent
            self.verbose = rt.verbose
            self.official = rt.official
            self.no_coverage = rt.no_coverage
            self.use_color = rt.use_color
            self.only_host = rt.only_host
            self.platform = rt.platform
            self.secrets = [*rt.secrets]

    def message(self, *args: str, level=Msg.DEBUG, **kwargs):
        if not MSG_GUARD[level](self):
            return

        print("--", *args, **kwargs, file=sys.stderr)

    def fatal(self, *args: str, **kwargs):
        print("-- FATAL:", *args, **kwargs, file=sys.stderr)
        sys.exit(1)

    def print(self, *args: str, raw=False):
        if not self.silent:
            Printer.print_cmd(
                *args, use_color=self.use_color, secrets=self.secrets, raw=raw
            )

    def cmd(self, *args: str):
        self.print(*args)
        if self.dry_run:
            return 0

        result = subprocess.run(args)
        if result.returncode != 0:
            print(
                f"proj-flow: error: {args[0]} ended in failure, exiting",
                file=sys.stderr,
            )
            return 1
        return 0

    def capture(self, *args: str, silent=False):
        if not silent:
            self.print(*args)
        return subprocess.run(args, shell=False, encoding="UTF-8", capture_output=True)

    def mkdirs(self, dirname: str):
        self.print("mkdir", "-p", dirname)

        if self.dry_run:
            return 0

        os.makedirs(dirname, exist_ok=True)
        return 0

    def cp(self, src: str, dst: str, regex: Optional[str] = None):
        args = ["cp"]
        if os.path.isdir(src):
            args.append("-r")
        self.print(*args, src, dst)

        if self.dry_run:
            return 0

        if regex is None:
            return _cp(src, dst)

        files = _ls(src)
        files = (name for name in files if re.match(regex, name))
        for name in files:
            result = _cp(os.path.join(src, name), os.path.join(dst, name))
            if result:
                return result
        return 0


@dataclass
class Config:
    items: dict
    keys: List[str]

    def get_path(self, key: str, val: Any = None):
        path = key.split(".")
        ctx = self.items
        for step in path:
            if not isinstance(ctx, dict):
                return val
            child = ctx.get(step)
            if child is None:
                return val
            ctx = child
        return cast(Any, ctx)

    @property
    def os(self) -> str:
        return self.items.get("os", "")

    @property
    def compiler(self) -> List[str]:
        return self.items.get("compiler", [])

    @property
    def build_type(self) -> str:
        return self.items.get("build_type", "")

    @property
    def build_name(self) -> str:
        return self.items.get("build_name", "")

    @property
    def build_dir(self) -> str:
        return os.path.join("build", self.preset)

    @property
    def preset(self) -> str:
        return self.items.get("preset", "")

    @property
    def build_generator(self) -> str:
        return self.items.get("build_generator", "")
