# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.base.plugins** provide the plugin enumeration helpers.
"""

import importlib
import json
import os
from types import ModuleType
from typing import Optional, cast

import yaml


def load_yaml(filename: str):
    with open(filename) as src:
        return cast(dict, yaml.load(src, Loader=yaml.Loader))


def load_json(filename: str):
    with open(filename) as src:
        return cast(dict, json.load(src))


LOADERS = {
    ".json": load_json,
    ".yml": load_yaml,
    ".yaml": load_yaml,
}


def load_data(filename: str):
    prefix, ext = os.path.splitext(filename)
    loader = LOADERS.get(ext.lower())
    if loader:
        try:
            return loader(filename)
        except Exception:
            pass

    for new_ext, loader in LOADERS.items():
        new_filename = prefix + new_ext
        try:
            return loader(new_filename)
        except Exception:
            pass

    return {}


def _load_plugins(directory: str, package: Optional[str], can_fail=False):
    for _, dirnames, filenames in os.walk(directory):
        for dirname in dirnames:
            if dirname == "__pycache__":
                continue

            try:
                importlib.import_module(f".{dirname}", package=package)
            except ModuleNotFoundError as err:
                if not can_fail:
                    raise err
        for filename in filenames:
            if filename == "__init__.py":
                continue

            try:
                importlib.import_module(
                    f".{os.path.splitext(filename)[0]}", package=package
                )
            except ModuleNotFoundError as err:
                if not can_fail:
                    raise err
        dirnames[:] = []


def load_module_plugins(mod: ModuleType, can_fail=False):
    spec = mod.__spec__
    if not spec:
        return
    for location in spec.submodule_search_locations:  # type: ignore
        _load_plugins(location, spec.name, can_fail)
