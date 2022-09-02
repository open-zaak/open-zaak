# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import re
import shutil
import uuid
from pathlib import Path, PurePath
from urllib.parse import urlparse

from django.conf import settings


def merge_files(part_files, file_dir, file_name) -> str:
    file_dir_path = Path(file_dir)
    file_dir_path.mkdir(exist_ok=True)
    file_path = file_dir_path / file_name
    with open(file_path, "wb") as output:
        for file in part_files:
            with file.open("rb") as fileobj:
                shutil.copyfileobj(
                    fileobj, output, settings.DOCUMENTEN_UPLOAD_READ_CHUNK
                )
    return file_path


def create_filename(name):
    path = PurePath(name)
    main_part, ext = path.stem, path.suffix
    ext = ext or f".{settings.DOCUMENTEN_UPLOAD_DEFAULT_EXTENSION}"
    return f"{main_part}{ext}"


def check_path(url, resource):
    # get_viewset_for_path can't be used since the external url can contain different subpathes
    path = urlparse(url).path
    # check general structure
    pattern = r".*/{}/(.+)".format(resource)
    match = re.match(pattern, path)
    if not match:
        return False

    # check uuid
    resource_id = match.group(1)
    try:
        uuid.UUID(resource_id)
    except ValueError:
        return False

    return True
