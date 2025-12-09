# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import DisallowedHost, ValidationError
from django.db import Error as DatabaseError, IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone

import structlog
from structlog.contextvars import bind_contextvars
from vng_api_common.constants import RelatieAarden
from vng_api_common.utils import generate_unique_identification

from openzaak import celery_app
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectSerializer,
)
from openzaak.components.documenten.import_utils import DocumentRow
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.zaken.models.zaken import Zaak, ZaakInformatieObject
from openzaak.import_data.models import Import, ImportStatusChoices
from openzaak.import_data.utils import (
    finish_batch,
    finish_import,
    get_csv_generator,
    get_total_count,
    task_locker,
)
from openzaak.utils.fields import get_default_path

logger = structlog.stdlib.get_logger(__name__)


def copy_file_to_storage(src: Path, dst: Path) -> str:
    """
    Util to copy a local file to the configured storage backend.
    Currently supports filesystem storage and Azure blob storage.

    :param src: path to the source file on disk
    :type src: Path
    :param dst: path where the file should be copied to in the storage backend
    :type dst: Path
    :return: the actual path on which the file is stored in the backend, this can be
        different from `dst` because characters can be appended to make the filename unique
    :rtype: str
    """
    default_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
    storage = EnkelvoudigInformatieObject.inhoud.field.storage

    if not settings.DOCUMENTEN_API_USE_AZURE_BLOB_STORAGE and not default_dir.exists():
        default_dir.mkdir(parents=True)

    if settings.DOCUMENTEN_API_USE_AZURE_BLOB_STORAGE:
        with open(src, "rb") as file:
            # A file could already exist at `dst` in the storage, so the actual path
            # to which the file ends up being saved is returned and stored on the
            # `EnkelvoudigInformatieObject.inhoud`
            name = storage.save(dst, file)
        return name
    else:
        shutil.copy2(src, dst)
        return str(dst)


def _import_document_row(
    row: list[str],
    row_index: int,
    identifier: str,
    existing_uuids: list[str],
    zaak_uuids: dict[str, int],
    request: HttpRequest,
) -> DocumentRow:
    expected_column_count = len(DocumentRow.import_headers)

    if len(row) < expected_column_count:
        error_message = (
            f"Validation failed for line {row_index}: insufficient column count"
        )

        logger.warning(
            "validation_failed_insufficient_column_count",
            row_index=row_index,
        )

        length = len(row)
        missing_count = expected_column_count - length

        missing_dummy_data = ["" for _i in range(missing_count)]
        data = [*row[:length], *missing_dummy_data, row_index]

        document_row = DocumentRow(*data)
        document_row.comment = error_message
        document_row.processed = True
        return document_row

    data = [*row[:expected_column_count], row_index]
    document_row = DocumentRow(*data)

    try:
        import_data = document_row.as_serializer_data()
    except Exception as e:
        error_message = f"Unable to import line {row_index}: {e}"

        logger.warning(
            "unable_to_import_line",
            row_index=row_index,
            error=str(e),
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    eio_serializer = EnkelvoudigInformatieObjectSerializer(
        data=import_data, context={"request": request}
    )

    try:
        if not eio_serializer.is_valid():
            error_message = (
                "A validation error occurred while deserializing a "
                f"EnkelvoudigInformatieObject on line {row_index}: \n"
                f"{eio_serializer.errors}"
            )

            logger.warning(
                "validation_error_during_deserialization",
                row_index=row_index,
                errors=eio_serializer.errors,
            )
            document_row.comment = error_message
            document_row.processed = True

            return document_row
    except DisallowedHost as e:
        error_message = f"Unable to import line {row_index}: {e}"

        logger.warning(
            "unable_to_import_line",
            row_index=row_index,
            error=str(e),
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    data: dict = eio_serializer.validated_data

    if document_row.uuid:
        try:
            uuid = UUID(document_row.uuid, version=4)
        except ValueError:
            error_message = (
                f"Given UUID for row {row_index} is not a valid UUID (version 4)"
            )

            logger.warning(
                "invalid_uuid_version_4",
                row_index=row_index,
            )
            document_row.comment = error_message
            document_row.processed = True

            return document_row

        if document_row.uuid in existing_uuids:
            error_message = (
                f"UUID given on row {row_index} was already found! Not overwriting "
                "existing EIO."
            )

            logger.warning(
                "duplicate_uuid_found_not_overwriting_eio",
                row_index=row_index,
            )
            document_row.comment = error_message
            document_row.processed = True

            return document_row

        data["uuid"] = str(uuid)
    else:
        data["uuid"] = str(uuid4())

    gegevensgroep_fields = ("ondertekening", "integriteit")

    for field in gegevensgroep_fields:
        gegevens_groep_value = data.pop(field, {})

        if not gegevens_groep_value:
            continue

        for key, value in gegevens_groep_value.items():
            data[f"{field}_{key}"] = value

    instance = EnkelvoudigInformatieObject(**data)
    instance.canonical = EnkelvoudigInformatieObjectCanonical()

    if not instance.identificatie:
        instance.identificatie = identifier

    zaak_uuid = document_row.zaak_uuid

    if zaak_uuid and zaak_uuid not in zaak_uuids:
        error_message = f"Zaak ID specified for row {row_index} is unknown."

        logger.warning(
            "unknown_zaak_id_specified",
            row_index=row_index,
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    try:
        instance.clean()
    except ValidationError as e:
        error_message = (
            "A validation error occurred while validating a "
            f"EnkelvoudigInformatieObject on line {row_index}: \n"
            f"{str(e)}"
        )

        logger.warning(
            "validation_error_validating_enkelvoudiginformatieobject",
            row_index=row_index,
            error=str(e),
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    file_path = document_row.bestandspad
    path = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR) / Path(file_path)

    if not path.exists() or not path.is_file():
        error_message = (
            f"The given filepath {path} does not exist or is not a file for "
            f"row {row_index}"
        )

        logger.warning(
            "invalid_filepath_for_row",
            path=str(path),
            row_index=row_index,
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    default_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
    import_path = default_dir / path.name

    try:
        actual_import_path = copy_file_to_storage(path, import_path)
    except Exception as e:
        error_message = f"Unable to copy file for row {row_index}: \n {str(e)}"

        logger.warning(
            "unable_to_copy_file",
            row_index=row_index,
            error=str(e),
        )
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    instance.inhoud.name = actual_import_path

    document_row.instance = instance
    return document_row


@transaction.atomic()
def _batch_create_eios(batch: list[DocumentRow], zaak_uuids: dict[str, int]) -> None:
    try:
        EnkelvoudigInformatieObjectCanonical.objects.bulk_create(
            [row.instance.canonical for row in batch if row.instance is not None]
        )
    except DatabaseError as e:
        for row in batch:
            row.processed = True
            row.comment = f"Unable to load row due to batch error: {str(e)}"

        raise e

    try:
        eios = EnkelvoudigInformatieObject.objects.bulk_create(
            [row.instance for row in batch if row.instance is not None]
        )
    except DatabaseError as e:
        for row in batch:
            row.processed = True
            row.comment = f"Unable to load row due to batch error: {str(e)}"

        raise e

    # reuse created instances
    for row in batch:
        if row.failed:
            continue

        instance = next(
            (
                eio
                for eio in eios
                if row.instance and str(eio.uuid) == str(row.instance.uuid)
            ),
            None,
        )

        row.instance = instance

        if not row.zaak_uuid:
            row.processed = True
            row.succeeded = bool(instance and instance.pk is not None)
            continue

        # Note that ZaakInformatieObject's will not be created using
        # `bulk_create` (see queryset MRO).
        zaak_eio = ZaakInformatieObject(
            zaak_id=zaak_uuids.get(row.zaak_uuid),
            informatieobject=instance.canonical,
            aard_relatie=RelatieAarden.from_object_type("zaak"),
        )

        try:
            zaak_eio.save()
        except DatabaseError as e:
            row.processed = True
            row.comment = (
                f"Unable to couple row {row.row_index} to ZAAK {row.zaak_uuid}:"
                f"\n {str(e)}"
            )

            for _row in batch:
                if _row.row_index == row.row_index:
                    continue

                _row.processed = True
                _row.comment = (
                    f"Unable to load row due to database error on row {row.row_index}"
                )

            raise e

        row.processed = True
        row.succeeded = True


def _get_identifiers(size: int) -> list[str]:
    now = timezone.now()
    dummy_instance = EnkelvoudigInformatieObject(creatiedatum=now.date())
    first_identifier = generate_unique_identification(dummy_instance, "creatiedatum")

    _range = size - 1 if size else 0  # don't count the first identifier

    model_name, year, number = first_identifier.split("-")
    number = int(number)
    identifiers = []

    for i in range(_range):
        number += 1

        identifiers.append(f"{model_name}-{year}-{str(number).zfill(10)}")

    return [first_identifier, *identifiers]


def _reconstruct_request(headers: dict) -> HttpRequest:
    """
    Reconstructs the HTTP request headers from the request the task originally was
    called from. Required for `django_loose_fk`.
    """
    request = HttpRequest()

    for key, value in headers.items():
        request.META[key] = value

    return request


# TODO: make this more generic?
@celery_app.task(bind=True)
@task_locker
def import_documents(self, import_pk: int, request_headers: dict) -> None:
    import_instance = Import.objects.get(pk=import_pk)

    request = _reconstruct_request(request_headers)

    file_path = import_instance.import_file.path

    bind_contextvars(import_id=import_pk, file_path=file_path)

    import_instance.total = get_total_count(file_path)
    import_instance.started_on = timezone.now()
    import_instance.status = ImportStatusChoices.active
    import_instance.save(update_fields=["total", "started_on", "status"])

    batch: list[DocumentRow] = []
    batch_size = settings.IMPORT_DOCUMENTEN_BATCH_SIZE

    zaak_uuids = {str(uuid): id for uuid, id in Zaak.objects.values_list("uuid", "id")}
    eio_uuids = [
        str(uuid) for uuid in EnkelvoudigInformatieObject.objects.values_list("uuid")
    ]

    identifiers = []

    for row_index, row in get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        if len(batch) % batch_size == 0:
            logger.info(
                "starting_batch",
                batch_number=import_instance.get_batch_number(batch_size),
            )

            identifiers = _get_identifiers(batch_size)

        document_row = _import_document_row(
            row, row_index, identifiers.pop(), eio_uuids, zaak_uuids, request
        )

        if document_row.instance and document_row.instance.uuid:
            eio_uuids.append(str(document_row.instance.uuid))

        batch.append(document_row)

        processed = import_instance.processed + len(batch)
        is_finished = bool(import_instance.total == processed)

        if len(batch) % batch_size != 0 and not is_finished:
            continue

        try:
            logger.debug(
                "creating_eios_and_zios_for_batch",
                batch_number=import_instance.get_batch_number(batch_size),
            )
            _batch_create_eios(batch, zaak_uuids)
        except IntegrityError as e:
            error_message = (
                "An Integrity error occured during batch "
                f"{import_instance.get_batch_number(batch_size)}: \n {str(e)}"
            )

            import_instance.comment += f"\n\n {error_message}"
            import_instance.save(update_fields=["comment"])

            logger.warning(
                "integrity_error_during_batch",
                batch_number=import_instance.get_batch_number(batch_size),
                error=str(e),
                next_batch=import_instance.get_batch_number(batch_size) + 1,
            )

        except DatabaseError as e:
            logger.critical(
                "critical_error_during_batch_finishing_import",
                batch_number=import_instance.get_batch_number(batch_size),
                error=str(e),
            )
            logger.info("trying_to_stop_import_process_gracefully")

            finish_batch(import_instance, batch, DocumentRow.export_headers)
            finish_import(
                import_instance,
                status=ImportStatusChoices.error,
                comment=str(e),
            )

            return

        finish_batch(import_instance, batch, DocumentRow.export_headers)

        remaining_batches = import_instance.get_remaining_batches(batch_size)
        logger.info(
            "batches_remaining",
            remaining_batches=remaining_batches,
        )
        batch.clear()

    finish_import(import_instance, ImportStatusChoices.finished)
