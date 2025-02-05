# Project Flow

[![Python package workflow badge](https://github.com/mzdun/proj-flow/actions/workflows/python-publish.yml/badge.svg)](https://github.com/mzdun/proj-flow/actions)
[![PyPI version badge](https://img.shields.io/pypi/v/proj-flow.svg)](https://pypi.python.org/pypi/proj-flow)
[![PyPI License: MIT](https://img.shields.io/pypi/l/proj-flow.svg)](https://pypi.python.org/pypi/proj-flow)

**Project Flow** aims at being a one-stop tool for C++ projects, from creating new
project, though building and verifying, all the way to publishing releases to
the repository. It will run a set of known steps and will happily consult your
project what do you want to call any subset of those steps.

Currently, it will make use of Conan for external dependencies, CMake presets
for config and build and GitHub CLI for releases.

## Installation

To create a new project with _Project Flow_, first install it using pip:

```sh
(.venv) $ pip install proj-flow
```

Every project created with _Project Flow_ has a self-bootstrapping helper script,
which will install `proj-flow` if it is needed, using either current virtual
environment or switching to a private virtual environment (created inside
`.flow/.venv` directory). This is used by the GitHub workflow in the generated
projects through the `bootstrap` command.

On any platform, this command (and any other) may be called from the root of the
project with:

```sh
python .flow/flow.py bootstrap
```

From Bash with:

```sh
./flow bootstrap
```

From PowerShell with:

```sh
.\flow bootstrap
```

## Creating a project

A fresh C++ project can be created with a

```sh
proj-flow init
```

This command will ask multiple questions to build Mustache context for the
project template. For more information, see [the documentation](https://proj-flow.readthedocs.io/en/latest/).
