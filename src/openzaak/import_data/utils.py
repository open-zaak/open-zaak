# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import csv
import functools
import logging
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Generator, Optional

from django.core.cache import cache
from django.db import DatabaseError
from django.utils import timezone

from openzaak.import_data.models import Import, ImportStatusChoices
from openzaak.utils.fields import get_default_path

logger = logging.getLogger(__name__)


def get_csv_generator(filename: str) -> Generator[tuple[int, list], None, None]:
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')

        index = 1

        for row in csv_reader:
            yield index, row

            index += 1


def get_total_count(filename: str, include_header: bool = False) -> int:
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        total = sum(1 for _ in csv_reader)

        if include_header:
            return total

        return total - 1 if total > 0 else 0


def get_batch_statistics(batch: list) -> tuple[int, int, int]:
    success_count = 0
    failure_count = 0
    processed_count = 0

    for row in batch:
        if not row.processed:
            continue

        if row.succeeded:
            success_count += 1
        elif row.failed:
            failure_count += 1

        processed_count += 1

    return processed_count, failure_count, success_count


def finish_import(
    instance: Import,
    status: ImportStatusChoices,
    finished_on: Optional[datetime] = None,
    comment: Optional[str] = "",
):
    updated_fields = ["finished_on", "status"]

    instance.finished_on = finished_on or timezone.now()
    instance.status = status

    if comment:
        instance.comment = comment

        updated_fields.append("comment")

    logger.info(f"Finishing import with status {status.label}")

    try:
        instance.save(update_fields=updated_fields)
    except DatabaseError as e:
        logger.critical(f"Unable to save import state due to database error: {str(e)}")


def finish_batch(import_instance: Import, batch: list, headers: list) -> None:
    batch_number = import_instance.get_batch_number(len(batch))
    _processed, _fail_count, _success_count = get_batch_statistics(batch)

    import_instance.processed = import_instance.processed + _processed
    import_instance.processed_successfully = (
        import_instance.processed_successfully + _success_count
    )
    import_instance.processed_invalid = import_instance.processed_invalid + _fail_count

    try:
        import_instance.save(
            update_fields=["processed", "processed_successfully", "processed_invalid"]
        )
    except DatabaseError as e:
        logger.critical(
            f"Unable to save batch statistics for batch {batch_number} due to database "
            f"error: {str(e)}"
        )

    logger.info(f"Writing batch number {batch_number} to report file")
    write_to_file(import_instance, batch, headers)

    logger.info(f"Removing files for unimported rows for batch number {batch_number}")
    cleanup_import_files(batch)


def cleanup_import_files(batch: list) -> None:
    for row in batch:
        if row.succeeded:
            continue

        path = row.imported_path

        if not path or not path.exists():
            continue

        logger.debug(f"Removing {path} for row {row.row_index}")

        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def write_to_file(instance: Import, batch: list, headers: list) -> None:
    """
    Note that this relies on (PrivateMedia)FileSystemStorage
    """
    default_dir = get_default_path(Import.report_file.field)
    default_name = f"report-{instance.pk}.csv"
    default_path = f"{default_dir}/{default_name}"

    if not default_dir.exists():
        default_dir.mkdir(parents=True)

    file_path = instance.report_file.file.name if instance.report_file else None
    file_exists = Path(instance.report_file.file.name).exists() if file_path else False
    has_data = bool(get_total_count(file_path)) if file_exists else False

    if file_exists and has_data:
        mode = "a"
    elif file_exists:
        mode = "w"
    else:
        mode = "w+"

    logger.debug(f"Using file mode {mode} for file {file_path or default_path}")

    with open(file_path or default_path, mode) as _export_file:
        csv_writer = csv.writer(_export_file, delimiter=",", quotechar='"')

        if mode in ("w", "w+"):
            csv_writer.writerow(headers)

        for row in batch:
            data = row.as_export_data()
            csv_writer.writerow(data.values())

    if file_path:
        return

    relative_path = Path(instance.report_file.field.upload_to) / default_name

    instance.report_file.name = str(relative_path)

    try:
        instance.save(update_fields=["report_file"])
    except DatabaseError as e:
        logger.critical(
            f"Unable to save new report file due to database error: {str(e)}"
        )


LOCK_EXPIRE = 60 * (60 * 24)  # 24 hours


@contextmanager
def task_lock(lock_id, oid):
    timeout_at = monotonic() + LOCK_EXPIRE - 3
    logger.info(f"Lock id {lock_id}:{oid} cache added.")
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        if monotonic() < timeout_at and status:
            logger.warning(f"Lock id {lock_id}:{oid} cache deleted")
            cache.delete(lock_id)


# Note that this not will not work with per process caches (e.g LocMemCache)
def task_locker(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        instance = args[0]
        lock_id = f"{instance.name}_lock"
        with task_lock(lock_id, instance.app.oid) as acquired:
            if acquired:
                return func(*args, **kwargs)
        logger.warning(f"Task {instance.name} already running, dispatch ignored...")

    return wrapped
