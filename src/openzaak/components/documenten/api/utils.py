# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import date
from pathlib import PurePath
from typing import IO
from urllib.parse import urlparse

from django.conf import settings
from django.core.files import File
from django.db.models import Max


def merge_files(part_files: Iterable[File[bytes]], dst: IO[bytes], /) -> None:
    """
    Write the contents of ``part_files`` to ``dst``, in order.
    """
    # TODO: in python 3.14 change type of dst to io.Writer[bytes]
    for file in part_files:
        with file.open("rb"):
            for chunk in file.chunks(settings.DOCUMENTEN_UPLOAD_READ_CHUNK):
                dst.write(chunk)


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


def generate_document_identificatie(
    bronorganisatie: str, date_value: date, aantal: int = 1
):
    from openzaak.components.documenten.models import (
        EnkelvoudigInformatieObject,
        ReservedDocument,
    )

    model_name = "DOCUMENT"

    year = date_value.year
    prefix = f"{model_name}-{year}"
    pattern = prefix + r"-\d{10}"

    issued_max = EnkelvoudigInformatieObject._default_manager.filter(
        identificatie__startswith=prefix,
        identificatie__regex=pattern,
    ).aggregate(Max("identificatie"))["identificatie__max"]

    reserved_max = ReservedDocument.objects.filter(
        bronorganisatie=bronorganisatie,
        identificatie__startswith=prefix,
        identificatie__regex=pattern,
    ).aggregate(Max("identificatie"))["identificatie__max"]

    def extract_number(identificatie):
        if identificatie is None:
            return 0
        return int(identificatie.split("-")[-1])

    max_number = max(extract_number(issued_max), extract_number(reserved_max))
    start_number = max_number + 1

    identificaties = [
        f"{prefix}-{str(i).zfill(10)}"
        for i in range(start_number, start_number + aantal)
    ]

    return identificaties[0] if aantal == 1 else identificaties
