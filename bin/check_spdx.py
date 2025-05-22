#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, List, Set

import click

SCAN_LINES = 5


@dataclass
class LanguageConfig:
    comment: str
    endcomment: str = ""


FILE_TYPES = {
    ".py": LanguageConfig(comment="#"),
    ".js": LanguageConfig(comment="//"),
    ".html": LanguageConfig(comment="<!--", endcomment="-->"),
    ".scss": LanguageConfig(comment="/*", endcomment="*/"),
}


@click.command()
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
    is_eager=True,
)
def main(src):
    root = os.path.abspath(os.curdir)
    sources: Set[Path] = set()

    gitignore_files = get_gitignore_files()

    for s in src:
        p = Path(s)
        if p.is_dir():
            sources.update(get_files_in_dir(p, root, gitignore_files))
        elif p.is_file() or s == "-":
            # if a file was explicitly given, we don't care about its extension
            sources.add(p)
        else:
            raise RuntimeError(f"invalid path: {s}")

    ok = True
    for source in sources:
        file_ok = check_file(source)
        if not file_ok:
            ok = False

    if not ok:
        sys.exit(1)


def get_gitignore_files():
    command = ["git", "ls-files", "--others", "--ignored", "--exclude-standard"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return [line for line in result.stdout.strip().split("\n") if line]


def get_files_in_dir(
    path: Path, root: Path, gitignore_files: List[str]
) -> Generator[Any, Any, Any]:
    assert os.path.isabs(root), f"INTERNAL ERROR: `root` must be absolute but is {root}"

    for child in path.iterdir():
        # First ignore files matching .gitignore
        if child.as_posix() in gitignore_files:
            continue

        # Then ignore with `exclude` option.
        try:
            normalized_path = "/" + child.resolve().relative_to(root).as_posix()
        except OSError:
            continue

        except ValueError:
            if child.is_symlink():
                continue

            raise

        if child.is_dir():
            normalized_path += "/"

        if child.is_dir():
            yield from get_files_in_dir(child, root, gitignore_files)

        elif child.is_file():
            yield child


def check_file(path: Path) -> bool:
    language = FILE_TYPES.get(path.suffix)
    if language is None:
        # nothing to do or check
        return True

    header = ""
    with path.open("r") as source_file:
        for i, line in enumerate(source_file.readlines()):
            if i >= SCAN_LINES:
                break
            header += line

    if "SPDX-License-Identifier" in header:
        return True

    print(f"File {path} seems to be mising the SPDX-License-Identifier header.")
    return False


if __name__ == "__main__":
    main()
