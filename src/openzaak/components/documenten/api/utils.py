# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import re
import shutil
import uuid
from datetime import date
from pathlib import Path, PurePath
from urllib.parse import urlparse

from django.conf import settings
from django.db import models


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


def generate_document_identificatie(
    bronorganisatie: str, document_model: models.Model, date_value: date
):
    from openzaak.components.documenten.models import ReservedDocument

    model_name = getattr(
        document_model, "IDENTIFICATIE_PREFIX", document_model._meta.model_name.upper()
    )
    year = date_value.year
    prefix = f"{model_name}-{year}"
    pattern = prefix + r"-\d{10}"

    issued_ids = document_model._default_manager.filter(
        identificatie__startswith=prefix,
        identificatie__regex=pattern,
    ).values_list("identificatie", flat=True)

    reserved_ids = ReservedDocument.objects.filter(
        bronorganisatie=bronorganisatie,
        identificatie__startswith=prefix,
        identificatie__regex=pattern,
    ).values_list("identificatie", flat=True)

    taken_ids = set(issued_ids).union(set(reserved_ids))

    number = 1
    while True:
        new_identificatie = f"{prefix}-{str(number).zfill(10)}"
        if new_identificatie not in taken_ids:
            return new_identificatie
        number += 1
