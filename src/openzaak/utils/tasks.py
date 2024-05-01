import binascii
import csv
import logging
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

from django.db import transaction
from django.utils.functional import classproperty

from celery.utils.serialization import base64encode
from rest_framework.test import APIRequestFactory
from vng_api_common.utils import generate_unique_identification

from openzaak import celery_app
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectSerializer,
)
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.utils.models import Import

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
        # TODO: remove quotes
        if not self._trefwoorden:
            return []

        return self._trefwoorden.split(",")

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
            "indicatieGebruiksrecht": self.indicatie_gebruiksrecht,
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
    document_row = DocumentRow(*row[:expected_column_count])

    logger.debug(f"Validating line {row_index}")

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

        logger.debug(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    data = eio_serializer.validated_data

    gegevensgroep_fields = ("ondertekening", "integriteit")

    for field in gegevensgroep_fields:
        gegevens_groep_value = data.pop(field, {})

        for key, value in gegevens_groep_value.items():
            data[f"{field}_{key}"] = value

    # TODO: call model `clean` method
    # TODO: follow EnkelvoudigInformatieObjectSerializer `create` behavior
    # TODO: handle features for `CMIS_ENABLED`?
    instance = EnkelvoudigInformatieObject(**data)
    document_row.instance = instance
    return document_row


@transaction.atomic()
def _batch_create_eios(batch: list[DocumentRow]) -> list[DocumentRow]:
    canonicals = []

    for row in batch:
        if row.instance is None:
            continue

        if not row.instance.identificatie:
            row.instance.identificatie = generate_unique_identification(
                row.instance, "creatiedatum"
            )

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
                if row.instance
                and eio.identificatie
                == row.instance.identificatie  # TODO: is this the correct identifier?
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


# TODO: ensure one task is running all the time
# TODO: make this more generic?
# TODO: expose `batch_size` through API?
@celery_app.task
def import_documents(import_pk: int, batch_size=500) -> None:
    import_instance = Import.objects.get(pk=import_pk)

    file_path = import_instance.import_file.path

    import_instance.total = _get_total_count(file_path)
    import_instance.save(update_fields=["total"])

    processed = 0
    fail_count = 0
    success_count = 0

    batch: list[DocumentRow] = []

    for row_index, row in _get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        document_row = _import_document_row(row, row_index)

        batch.append(document_row)

        if not len(batch) % batch_size == 0:
            continue

        created_batch: list[DocumentRow] = _batch_create_eios(batch)

        _processed, _fail_count, _success_count = _get_batch_statistics(created_batch)

        processed += _processed
        fail_count += _fail_count
        success_count += _success_count

        # TODO: couple eio's to zaken after bulk_create

        import_instance.processed = processed
        import_instance.processed_succesfully = success_count
        import_instance.processed_invalid = fail_count
        import_instance.save(
            update_fields=["processed", "processed_succesfully", "processed_invalid"]
        )

        logger.debug(f"Writing batch number {processed / batch_size} to report file")
        # TODO: implement writing batch to report file. Use append file mode when
        # writing to existing report file.

        batch.clear()
