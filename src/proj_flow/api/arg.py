# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.api.arg** is used by various commands to declare CLI arguments.
"""

import argparse
import inspect
import typing
from dataclasses import dataclass, field

from proj_flow.base import inspect as _inspect


@dataclass
class Argument:
    help: str = ""
    pos: bool = False
    names: typing.List[str] = field(default_factory=list)
    nargs: typing.Union[str, int, None] = None
    opt: typing.Optional[bool] = None
    meta: typing.Optional[str] = None
    action: typing.Union[str, argparse.Action, None] = None
    default: typing.Optional[typing.Any] = None
    choices: typing.Optional[typing.List[str]] = None
    completer: typing.Optional[callable] = None  # type: ignore

    def visit(self, parser: argparse.ArgumentParser, name: str):
        kwargs = {}
        if self.help is not None:
            kwargs["help"] = self.help
        if self.nargs is not None:
            kwargs["nargs"] = self.nargs
        if self.meta is not None:
            kwargs["metavar"] = self.meta
        if self.default is not None:
            kwargs["default"] = self.default
        if self.action is not None:
            kwargs["action"] = self.action
        if self.choices is not None:
            kwargs["choices"] = self.choices

        names = (
            [name] if self.pos else self.names if len(self.names) > 0 else [f"--{name}"]
        )

        if self.pos:
            kwargs["nargs"] = "?" if self.opt else 1
        else:
            kwargs["dest"] = name
            kwargs["required"] = not self.opt

        action = parser.add_argument(*names, **kwargs)
        if self.completer:
            action.completer = self.completer  # type: ignore

        return action


class FlagArgument(Argument):
    def __init__(self, help: str = "", names: typing.List[str] = []):
        super().__init__(
            help=help, names=names, opt=True, action="store_true", default=False
        )


@dataclass
class _Command:
    name: str
    entry: typing.Optional[callable]  # type: ignore
    doc: typing.Optional[str]
    subs: typing.Dict[str, "_Command"]

    def add(self, names: typing.List[str], entry: callable, doc: typing.Optional[str]):  # type: ignore
        name = names[0]
        rest = names[1:]
        if len(rest):
            try:
                child = self.subs[name]
            except KeyError:
                child = _Command(name, None, None, {})
                self.subs[name] = child

            child.add(rest, entry, doc)
            return

        try:
            child = self.subs[name]
            child.entry = entry
            child.doc = doc
        except KeyError:
            self.subs[name] = _Command(name, entry, doc, {})


_known_commands = _Command("", None, None, {})
_autodoc = {
    "proj_flow.flow.configs.Configs": "Current configuration list.",
    "proj_flow.api.env.Runtime": "Tools and print messages, while respecting ``--dry-run``, ``--silent`` and ``--verbose``.",
}


def command(*name: str):
    def wrap(entry: callable):  # type: ignore
        global _known_commands
        orig_doc = inspect.getdoc(entry)
        _known_commands.add(list(name), entry, orig_doc)

        doc = orig_doc or ""
        if doc:
            doc += "\n\n"

        for arg in _inspect.signature(entry):
            help = ""
            for meta in arg.metadata:
                if isinstance(meta, Argument):
                    help = meta.help
                    if help:
                        break

            if not help:
                full_name = f"{arg.type.__module__}.{arg.type.__name__}"
                help = _autodoc.get(full_name, "")

            doc += f":param {_inspect.type_name(arg.type)} {arg.name}: {help}\n"

        entry.__doc__ = doc

        return entry

    return wrap


def get_commands():
    return _known_commands
