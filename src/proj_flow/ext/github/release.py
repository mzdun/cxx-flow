# Copyright (c) 2025 Marcin Zdun
# This code is licensed under MIT license (see LICENSE for details)

"""
The **proj_flow.plugins.commands.ci.release** implements
``./flow ci release`` command.
"""

import typing

from proj_flow.api import arg, env
from proj_flow.log import commit, fmt, hosting, release, rich_text
from proj_flow.plugins import cmake

FORCED_LEVEL_CHOICES = list(commit.FORCED_LEVEL.keys())


def _name_list(names: typing.List[str]) -> str:
    if len(names) == 0:
        return ""

    prefix = ", ".join(names[:-1])
    if prefix:
        prefix += " and "
    return f"{prefix}{names[-1]}"


def _bump_version(ver: str, level: commit.Level):
    split = ver.split("-", 1)
    if len(split) == 2:
        stability = f"-{split[1]}"
    else:
        stability = ""

    semver = [int(s) for s in split[0].split(".")]
    while len(semver) < 3:
        semver.append(0)
    semver = semver[:3]

    if level.value > commit.Level.BENIGN.value:
        # This turns [1, 2, 3] through 4 - x into [3, 2, 1]
        lvl = commit.Level.BREAKING.value - level.value
        semver[lvl] += 1
        for index in range(lvl + 1, len(semver)):
            semver[index] = 0

    return ".".join(str(v) for v in semver) + stability


@arg.command("github", "release")
def main(
    rt: env.Runtime,
    all: typing.Annotated[
        bool, arg.FlagArgument(help="Take all Conventional Commits.")
    ],
    force: typing.Annotated[
        typing.Optional[str],
        arg.Argument(
            help="Ignore the version change from changelog and instead use this value. "
            f"Allowed values are: {_name_list(FORCED_LEVEL_CHOICES)}",
            meta="level",
            choices=FORCED_LEVEL_CHOICES,
        ),
    ],
    stability: typing.Annotated[
        typing.Optional[str],
        arg.Argument(help="Change the stability of the version.", meta="value"),
    ],
):
    """
    Bumps the project version based on current git logs, creates a "chore"
    commit for the change, attaches an annotated tag with the version number
    and pushes it all to GitHub.
    """
    generator = rich_text.markdown.ChangelogGenerator()

    forced_level = commit.FORCED_LEVEL.get(force) if force else None

    project = cmake.parser.get_project(rt.root)
    if not project:
        rt.fatal("No CMakeLists.txt with project() found.")

    git = commit.Git(rt)
    tags = git.tag_list(silent=True)
    gh_links = hosting.github.GitHub.from_repo(git)

    prev_tag = tags[-1] if len(tags) > 0 else None

    setup = commit.LogSetup(gh_links, prev_tag, None, take_all=all)
    log, log_level = git.get_log(setup)

    project_version = f"{project.version.value}{project.stability.value}"
    next_version = _bump_version(project_version, forced_level or log_level)
    setup.curr_tag = f"v{next_version}"

    if setup.curr_tag in tags:
        rt.fatal(f"Tag {setup.curr_tag} already exists.")

    files_to_commit: typing.List[str] = []
    if not rt.dry_run and project_version != next_version:
        files_to_commit.extend(generator.update_changelog(log, setup, rt))
        files_to_commit.extend(project.set_version(rt.root, next_version))
        # TODO: plugins for other places a version would need to be updated

    commit_message = f"release {next_version}"
    git.add_files(*files_to_commit)
    git.commit(f"chore: {commit_message}{fmt.format_commit_message(log)}")
    git.annotated_tag(setup.curr_tag, commit_message)

    if gh_links.is_active:
        draft_url = gh_links.draft_a_release(log, setup, git).draft_url
        if draft_url:
            rt.message("-- Visit draft at", draft_url, level=env.Msg.ALWAYS)

    print()

    print(project_version, "->", next_version)
