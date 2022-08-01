# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import os
import shutil

from django.conf import settings


def merge_files(part_files, file_dir, file_name) -> str:
    os.makedirs(file_dir, exist_ok=True)

    file_path = os.path.join(file_dir, file_name)
    with open(file_path, "wb") as output:
        for file in part_files:
            with file.open("rb") as fileobj:
                shutil.copyfileobj(fileobj, output, settings.READ_CHUNK)
    return file_path


def create_filename(name):
    main_part, ext = os.path.splitext(name)
    ext = ext or f".{settings.DEFAULT_EXTENSION}"
    return f"{main_part}{ext}"
