import binascii
import csv
import logging
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.functional import classproperty

from celery.utils.serialization import base64encode
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
from openzaak.utils.models import Import, ImportStatusChoices

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
        return [*cls.import_headers, "opmerking"]

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
    def inhoud(self) -> Optional[str]:
        if not self._bestandspad:
            return None

        path = Path(self._bestandspad)

        if not path.exists() or not path.is_file():
            raise IOError("The given filepath does not exist or is not a file.")

        with open(path, "rb") as import_file:
            file_contents = import_file.read()
            import_file.seek(0)

        if not file_contents:
            return None

        is_base64 = False

        try:
            is_base64 = b64decode(file_contents, validate=True)
        except binascii.Error:
            is_base64 = False

        if is_base64:
            return b64decode(file_contents)

        return base64encode(file_contents).decode("ascii")

    @property
    def bestandsomvang(self) -> Optional[int]:
        if not self._bestandsomvang:
            return None

        return int(self._bestandsomvang)

    @property
    def indicatie_gebruiksrecht(self) -> bool:
        # TODO: fix this
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
            "inhoud": self.inhoud,
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
            "opmerking": self.comment,
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
        data["vertrouwelijkheidaanduiding"] = (
            informatieobjecttype.vertrouwelijkheidaanduiding
        )

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

    if instance.bestandsomvang == 0:
        instance.inhoud.save("empty_file", ContentFile(""))

    # TODO: handle large files? See `EnkelvoudigInformatieObjectSerializer`
    # TODO: handle features for `CMIS_ENABLED`? See `EnkelvoudigInformatieObjectSerializer`

    document_row.instance = instance
    return document_row


# TODO: catch this function call
@transaction.atomic()
def _batch_create_eios(batch: list[DocumentRow]) -> list[DocumentRow]:
    canonicals = []

    for row in batch:
        if row.instance is None:
            continue

        canonical = EnkelvoudigInformatieObjectCanonical()
        row.instance.canonical = canonical

        canonicals.append(canonical)

    EnkelvoudigInformatieObjectCanonical.objects.bulk_create(canonicals)

    eios = EnkelvoudigInformatieObject.objects.bulk_create(
        [row.instance for row in batch if row.instance is not None]
    )

    # reuse created instances
    for row in batch:
        instance = next(
            (
                eio
                for eio in eios
                if row.instance and eio.uuid == row.instance.uuid
            ),
            None,
        )

        row.instance = instance

        if not row.zaak_id:
            row.processed = True
            row.succeeded = True if instance and instance.pk is not None else False

    return batch


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


# TODO: catch this function call
@transaction.atomic()
def _batch_couple_eios(
    batch: list[DocumentRow], zaak_uuids: dict[str, int]
) -> list[DocumentRow]:
    """
    Note that ZaakInformatieObject's will not be created in bulk (see queryset MRO).
    """
    zaak_rows = [row for row in batch if row.has_instance and row.zaak_id]

    for row in zaak_rows:
        if row.zaak_id not in zaak_uuids:
            error_message = (
                f"Provided zaak UUID {row.zaak_id} for line {row.row_index} is "
                "unknown. Unable to couple EnkelvoudigInformatieObject to Zaak."
            )
            logger.warning(error_message)
            row.comment = error_message
            row.processed = True
            continue

        zaak_eio = ZaakInformatieObject(
            zaak_id=zaak_uuids[row.zaak_id],
            informatieobject=row.instance.canonical,
            aard_relatie=RelatieAarden.from_object_type("zaak"),
        )

        zaak_eio.save()

        row.processed = True
        row.succeeded = True

    return batch


def _write_to_file(instance: Import, batch: list[DocumentRow]) -> None:
    """
    Note that this relies on (PrivateMedia)FileSystemStorage
    """
    storage_location = Path(instance.report_file.storage.base_location)
    default_dir = Path(storage_location / instance.report_file.field.upload_to)
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
            data = row.as_original()
            csv_writer.writerow(data.values())

    if file_path:
        return

    relative_path = Path(instance.report_file.field.upload_to) / default_name

    instance.report_file.name = str(relative_path)
    instance.save(update_fields=["report_file"])


# TODO: ensure one task is running all the time
# TODO: make this more generic?
# TODO: expose `batch_size` through API?
@celery_app.task
def import_documents(import_pk: int, batch_size=500) -> None:
    import_instance = Import.objects.get(pk=import_pk)

    file_path = import_instance.import_file.path

    import_instance.total = _get_total_count(file_path)
    import_instance.started_on = timezone.now()
    import_instance.status = ImportStatusChoices.active
    import_instance.save(update_fields=["total", "started_on", "status"])

    processed = 0
    fail_count = 0
    success_count = 0

    batch: list[DocumentRow] = []
    batch_number = int(processed / batch_size) + 1

    zaak_uuids = {str(uuid): id for uuid, id in Zaak.objects.values_list("uuid", "id")}

    for row_index, row in _get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        if len(batch) % batch_size == 0:
            logger.info(f"Starting batch {batch_number}")

        document_row = _import_document_row(row, row_index)

        batch.append(document_row)

        if not len(batch) % batch_size == 0:
            continue

        logger.debug(f"Creating EIO's for batch {batch_number}")
        created_batch: list[DocumentRow] = _batch_create_eios(batch)

        logger.debug(f"Coupling EIO's to Zaken for for batch {batch_number}")
        _batch = _batch_couple_eios(created_batch, zaak_uuids)

        _processed, _fail_count, _success_count = _get_batch_statistics(_batch)

        processed += _processed
        fail_count += _fail_count
        success_count += _success_count

        import_instance.processed = processed
        import_instance.processed_succesfully = success_count
        import_instance.processed_invalid = fail_count
        import_instance.save(
            update_fields=["processed", "processed_succesfully", "processed_invalid"]
        )

        logger.info(f"Writing batch number {batch_number} to report file")
        _write_to_file(import_instance, _batch)

        remaining_batches = int(
            (import_instance.total / batch_size) - (processed / batch_size)
        )

        logger.info(f"{remaining_batches} batches remaining")

        batch_number = int(processed / batch_size) + 1
        batch.clear()

    import_instance.finished_on = timezone.now()
    # TODO: determine status based on import errors occured
    import_instance.status = ImportStatusChoices.finished
    import_instance.save(update_fields=["finished_on", "status"])
