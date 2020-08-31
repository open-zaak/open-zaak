#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

import click
from black import find_project_root, get_gitignore
from pathspec import PathSpec

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
    # Path handling inspired on the implementation of Black: https://github.com/psf/black
    root = find_project_root(src)
    gitignore = get_gitignore(root)
    sources: Set[Path] = set()

    for s in src:
        p = Path(s)
        if p.is_dir():
            sources.update(get_files_in_dir(p, root, gitignore))
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


def get_files_in_dir(path: Path, root: Path, gitignore: PathSpec) -> List[Path]:
    assert root.is_absolute(), f"INTERNAL ERROR: `root` must be absolute but is {root}"
    for child in path.iterdir():
        # First ignore files matching .gitignore
        if gitignore.match_file(child.as_posix()):
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
            yield from get_files_in_dir(child, root, gitignore)

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
