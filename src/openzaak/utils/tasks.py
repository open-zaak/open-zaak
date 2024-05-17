import csv
import functools
import logging
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Generator, Optional
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import Error as DatabaseError, IntegrityError, transaction
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from django.utils.functional import classproperty

from rest_framework.test import APIRequestFactory
from vng_api_common.constants import RelatieAarden
from vng_api_common.utils import generate_unique_identification

from openzaak import celery_app
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectSerializer,
)
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.zaken.models.zaken import Zaak, ZaakInformatieObject
from openzaak.utils.models import Import, ImportRowResultChoices, ImportStatusChoices

logger = logging.getLogger(__name__)


def _get_csv_generator(filename: str) -> Generator[tuple[int, list], None, None]:
    with open(filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')

        index = 1

        for row in csv_reader:
            yield index, row

            index += 1


def _get_total_count(filename: str, include_header: bool = False) -> int:
    with open(filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        total = sum(1 for _ in csv_reader)

        if include_header:
            return total

        return total - 1 if total > 0 else 0


@dataclass
class DocumentRow:
    _identificatie: str
    _bronorganisatie: str
    _creatiedatum: str
    _titel: str
    _vertrouwelijkheidaanduiding: str
    _auteur: str
    _status: str
    _formaat: str
    _taal: str

    _bestandsnaam: str
    _bestandsomvang: str
    _bestandspad: str

    _link: str
    _beschrijving: str
    _indicatie_gebruiksrecht: str
    _verschijningsvorm: str

    _ondertekening_soort: str
    _ondertekening_datum: str

    _integriteit_algoritme: str
    _integriteit_waarde: str
    _integriteit_datum: str

    _informatieobjecttype: str
    _zaak_id: str
    _trefwoorden: str

    row_index: int

    comment: Optional[str] = None
    instance: Optional[EnkelvoudigInformatieObject] = None

    _processed: bool = False
    _succeeded: bool = False

    @classproperty
    def import_headers(cls) -> list[str]:
        return [
            "identificatie",
            "bronorganisatie",
            "creatiedatum",
            "titel",
            "vertrouwelijkheidaanduiding",
            "auteur",
            "status",
            "formaat",
            "taal",
            "bestandsnaam",
            "bestandsomvang",
            "bestandspad",
            "link",
            "beschrijving",
            "indicatieGebruiksrecht",
            "verschijningsvorm",
            "ondertekening.soort",
            "ondertekening.datum",
            "integriteit.algoritme",
            "integriteit.waarde",
            "integriteit.datum",
            "informatieobjecttype",
            "zaakId",
            "trefwoorden",
        ]

    @classproperty
    def export_headers(cls) -> list[str]:
        return [*cls.import_headers, "opmerking", "resultaat"]

    @property
    def bronorganisatie(self) -> str:
        return self._bronorganisatie

    @property
    def creatiedatum(self) -> Optional[str]:
        return self._creatiedatum or None

    @property
    def titel(self) -> Optional[str]:
        return self._titel or None

    @property
    def auteur(self) -> Optional[str]:
        return self._auteur or None

    @property
    def taal(self) -> Optional[str]:
        return self._taal or None

    @property
    def bestandspad(self) -> str:
        return self._bestandspad

    @property
    def bestandsomvang(self) -> Optional[int]:
        if not self._bestandsomvang:
            return None

        return int(self._bestandsomvang)

    @property
    def indicatie_gebruiksrecht(self) -> bool:
        return self._indicatie_gebruiksrecht in ("True", "true")

    @property
    def ondertekening(self) -> Optional[dict]:
        if not any((self._ondertekening_soort, self._ondertekening_datum,)):
            return None

        return {
            "soort": self._ondertekening_soort,
            "datum": self._ondertekening_datum,
        }

    @property
    def integriteit(self) -> Optional[dict]:
        if not any(
            (
                self._integriteit_datum,
                self._integriteit_waarde,
                self._integriteit_algoritme,
            )
        ):
            return None

        return {
            "algoritme": self._integriteit_algoritme,
            "waarde": self._integriteit_waarde,
            "datum": self._integriteit_datum,
        }

    @property
    def zaak_id(self) -> Optional[str]:
        return self._zaak_id

    @property
    def trefwoorden(self) -> list[str]:
        if not self._trefwoorden:
            return []

        trefwoorden = self._trefwoorden.replace('"', "")

        if not trefwoorden:
            return []

        return trefwoorden.split(",")

    @property
    def processed(self) -> bool:
        return self._processed

    @processed.setter
    def processed(self, value: bool):
        self._processed = value

    @property
    def succeeded(self) -> bool:
        return self.processed and self._succeeded

    @succeeded.setter
    def succeeded(self, value: bool):
        self._succeeded = value

    @property
    def failed(self) -> bool:
        return self.processed and not self.succeeded

    @property
    def has_instance(self) -> bool:
        return bool(self.instance and self.instance.pk)

    @property
    def result(self):
        if self.succeeded:
            return ImportRowResultChoices.imported.label

        return ImportRowResultChoices.not_imported.label

    def as_serializer_data(self):
        return {
            "identificatie": self._identificatie,
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": self.creatiedatum,
            "titel": self.titel,
            "vertrouwelijkheidaanduiding": self._vertrouwelijkheidaanduiding,
            "auteur": self.auteur,
            "status": self._status,
            "formaat": self._formaat,
            "taal": self.taal,
            "bestandsnaam": self._bestandsnaam,
            "bestandsomvang": self.bestandsomvang,
            "link": self._link,
            "beschrijving": self._beschrijving,
            "indicatie_gebruiksrecht": self.indicatie_gebruiksrecht,
            "verschijningsvorm": self._verschijningsvorm,
            "ondertekening": self.ondertekening,
            "integriteit": self.integriteit,
            "informatieobjecttype": self._informatieobjecttype,
            "trefwoorden": self.trefwoorden,
        }

    def as_original(self):
        return {
            "identificatie": self._identificatie,
            "bronorganisatie": self._bronorganisatie,
            "creatiedatum": self._creatiedatum,
            "titel": self._titel,
            "vertrouwelijkheidaanduiding": self._vertrouwelijkheidaanduiding,
            "auteur": self._auteur,
            "status": self._status,
            "formaat": self._formaat,
            "taal": self._taal,
            "bestandsnaam": self._bestandsnaam,
            "bestandsomvang": self._bestandsomvang,
            "bestandspad": self._bestandspad,
            "link": self._link,
            "beschrijving": self._beschrijving,
            "indicatieGebruiksrecht": self._indicatie_gebruiksrecht,
            "verschijningsvorm": self._verschijningsvorm,
            "ondertekening.soort": self._ondertekening_soort,
            "ondertekening.datum": self._ondertekening_datum,
            "integriteit.algoritme": self._integriteit_algoritme,
            "integriteit.waarde": self._integriteit_waarde,
            "integriteit.datum": self._integriteit_datum,
            "informatieobjecttype": self._informatieobjecttype,
            "zaakId": self._zaak_id,
            "trefwoorden": self._trefwoorden,
        }

    def as_export_data(self):
        return {
            **self.as_original(),
            "opmerking": self.comment,  # TODO: verify this is formatted properly
            "resultaat": self.result,
        }


def _import_document_row(row: list[str], row_index: int) -> DocumentRow:
    expected_column_count = len(DocumentRow.import_headers)

    request_factory = APIRequestFactory()
    request = request_factory.get("/")

    # TODO: is this possible with an invalid row count?
    data = [*row[:expected_column_count], row_index]
    document_row = DocumentRow(*data)

    if len(row) < expected_column_count:
        error_message = (
            f"Validation failed for line {row_index}: insufficient row count"
        )

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    try:
        import_data = document_row.as_serializer_data()
    except Exception as e:
        error_message = f"Unable to import line {row_index}: {e}"

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    eio_serializer = EnkelvoudigInformatieObjectSerializer(
        data=import_data, context={"request": request}
    )

    if not eio_serializer.is_valid():
        error_message = (
            "A validation error occurred while deserializing a "
            "EnkelvoudigInformtatieObject on line %(row_index)s: \n"
            "%(errors)s"
        ) % dict(row_index=row_index, errors=eio_serializer.errors)

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    data: dict = eio_serializer.validated_data

    gegevensgroep_fields = ("ondertekening", "integriteit")

    for field in gegevensgroep_fields:
        gegevens_groep_value = data.pop(field, {})

        for key, value in gegevens_groep_value.items():
            data[f"{field}_{key}"] = value

    data["uuid"] = str(uuid4())

    if "vertrouwelijkheidaanduiding" not in data:
        informatieobjecttype = data["informatieobjecttype"]
        data[
            "vertrouwelijkheidaanduiding"
        ] = informatieobjecttype.vertrouwelijkheidaanduiding

    instance = EnkelvoudigInformatieObject(**data)

    if not instance.identificatie:
        instance.identificatie = generate_unique_identification(
            instance, "creatiedatum"
        )

    try:
        instance.clean()
    except ValidationError as e:
        error_message = (
            "A validation error occurred while validating a "
            "EnkelvoudigInformtatieObject on line %(row_index)s: \n"
            "%(error)s"
        ) % dict(row_index=row_index, error=str(e))

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    file_path = document_row.bestandspad
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        error_message = (
            "The given filepath %(file_path)s does not exist or is a file for "
            "row %(row_index)s"
        ) % dict(file_path=file_path, row_index=row_index)

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    default_dir = _get_default_path(instance.inhoud)
    import_path = f"{default_dir}/{path.name}"

    if not default_dir.exists():
        default_dir.mkdir(parents=True)

    try:
        shutil.copy2(file_path, import_path)
    except Exception as e:
        error_message = (
            "Unable to copy file for row %(row_index)s: \n %(error)s"
        ) % dict(error=str(e), row_index=row_index)

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    instance.inhoud.name = str(import_path)

    document_row.instance = instance
    return document_row


@transaction.atomic()
def _batch_create_eios(batch: list[DocumentRow], zaak_uuids: dict[str, int]) -> None:
    canonicals = []

    for row in batch:
        if row.instance is None:
            continue

        canonical = EnkelvoudigInformatieObjectCanonical()
        row.instance.canonical = canonical

        canonicals.append(canonical)

    try:
        EnkelvoudigInformatieObjectCanonical.objects.bulk_create(canonicals)
    except IntegrityError as e:
        for row in batch:
            row.processed = True
            row.comment = f"Unable to load row due to batch error: {str(e)}"

        raise e

    try:
        eios = EnkelvoudigInformatieObject.objects.bulk_create(
            [row.instance for row in batch if row.instance is not None]
        )
    except IntegrityError as e:
        for row in batch:
            row.processed = True
            row.comment = f"Unable to load row due to batch error: {str(e)}"

        raise e

    # reuse created instances
    for row in batch:
        instance = next(
            (eio for eio in eios if row.instance and eio.uuid == row.instance.uuid),
            None,
        )

        row.instance = instance

        if not row.zaak_id:
            row.processed = True
            row.succeeded = True if instance and instance.pk is not None else False
            continue

        # Note that ZaakInformatieObject's will not be created using
        # `bulk_create` (see queryset MRO).
        zaak_eio = ZaakInformatieObject(
            zaak_id=zaak_uuids.get(row.zaak_id),
            informatieobject=instance.canonical,
            aard_relatie=RelatieAarden.from_object_type("zaak"),
        )

        try:
            zaak_eio.save()
        except IntegrityError as e:
            row.processed = True
            row.comment = (
                f"Unable to couple row {row.row_index} to ZAAK {row.zaak_id}:"
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


def _get_batch_statistics(batch: list[DocumentRow]) -> tuple[int, int, int]:
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


def _get_default_path(field: FieldFile) -> Path:
    storage_location = Path(field.storage.base_location)
    path = Path(storage_location / field.field.upload_to)

    now = timezone.now()
    return Path(now.strftime(str(path)))


def _write_to_file(instance: Import, batch: list[DocumentRow]) -> None:
    """
    Note that this relies on (PrivateMedia)FileSystemStorage
    """
    default_dir = _get_default_path(instance.report_file)
    default_name = f"report-{instance.pk}.csv"
    default_path = f"{default_dir}/{default_name}"

    if not default_dir.exists():
        default_dir.mkdir(parents=True)

    file_path = instance.report_file.file.name if instance.report_file else None
    file_exists = Path(instance.report_file.file.name).exists() if file_path else False
    has_data = bool(_get_total_count(file_path)) if file_exists else False

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
            csv_writer.writerow(DocumentRow.export_headers)

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


def _finish_import(
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

    try:
        instance.save(update_fields=updated_fields)
    except DatabaseError as e:
        logger.critical(f"Unable to save import state due to database error: {str(e)}")


def _finish_batch(import_instance: Import, batch: list[DocumentRow],) -> None:
    batch_number = import_instance.get_batch_number(len(batch))
    _processed, _fail_count, _success_count = _get_batch_statistics(batch)

    import_instance.processed = import_instance.processed + _processed
    import_instance.processed_succesfully = (
        import_instance.processed_succesfully + _success_count
    )
    import_instance.processed_invalid = import_instance.processed_invalid + _fail_count

    try:
        import_instance.save(
            update_fields=["processed", "processed_succesfully", "processed_invalid"]
        )
    except DatabaseError as e:
        logger.critical(
            f"Unable to save batch statistics for batch {batch_number} due to database "
            f"error: {str(e)}"
        )

    logger.info(f"Writing batch number {batch_number} to report file")
    _write_to_file(import_instance, batch)


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


# TODO: make this more generic?
@celery_app.task(bind=True)
@task_locker
def import_documents(self, import_pk: int) -> None:
    import_instance = Import.objects.get(pk=import_pk)

    file_path = import_instance.import_file.path

    import_instance.total = _get_total_count(file_path)
    import_instance.started_on = timezone.now()
    import_instance.status = ImportStatusChoices.active
    import_instance.save(update_fields=["total", "started_on", "status"])

    batch: list[DocumentRow] = []
    batch_size = settings.IMPORT_DOCUMENTEN_BATCH_SIZE

    zaak_uuids = {str(uuid): id for uuid, id in Zaak.objects.values_list("uuid", "id")}

    for row_index, row in _get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        if len(batch) % batch_size == 0:
            logger.info(
                f"Starting batch {import_instance.get_batch_number(batch_size)}"
            )

        document_row = _import_document_row(row, row_index)

        batch.append(document_row)

        if not len(batch) % batch_size == 0:
            continue

        try:
            logger.debug(
                "Creating EIO's and ZEIO's for batch "
                f"{import_instance.get_batch_number(batch_size)}"
            )
            _batch_create_eios(batch, zaak_uuids)
        except IntegrityError as e:
            error_message = (
                f"An Integrity error occured during batch "
                f"{import_instance.get_batch_number(batch_size)}: \n {str(e)}"
            )

            import_instance.comment += f"\n\n {error_message}"
            import_instance.save(update_fields=["comment"])

            logger.warning(
                f"{error_message} \n Trying to continue with batch "
                f"{import_instance.get_batch_number(batch_size) + 1}"
            )

        except DatabaseError as e:
            logger.critical(
                f"A critical error occured during batch "
                f"{import_instance.get_batch_number(batch_size)}. "
                f"Finishing import due to database error: \n{str(e)}"
            )
            logger.info("Trying to stop the import process gracefully")

            _finish_batch(import_instance, batch)
            _finish_import(
                import_instance, status=ImportStatusChoices.error, comment=str(e),
            )

            return

        _finish_batch(import_instance, batch)

        remaining_batches = import_instance.get_remaining_batches(batch_size)
        logger.info(f"{remaining_batches} batches remaining")

        batch.clear()

    _finish_import(import_instance, ImportStatusChoices.finished)
