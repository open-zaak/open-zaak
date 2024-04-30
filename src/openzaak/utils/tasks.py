import binascii
import csv
import logging
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils.functional import classproperty

from celery.utils.serialization import base64encode
from rest_framework.test import APIRequestFactory
from vng_api_common.constants import RelatieAarden

from openzaak import celery_app
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectSerializer,
)
from openzaak.components.zaken.models.zaken import Zaak, ZaakInformatieObject
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
    identificatie: str
    bronorganisatie: str
    creatiedatum: str
    titel: str
    vertrouwelijkheidaanduiding: str
    auteur: str
    status: str
    formaat: str
    taal: str

    bestandsnaam: str
    bestandsomvang: str
    bestandspad: str

    link: str
    beschrijving: str
    indicatie_gebruiksrecht: str
    verschijningsvorm: str

    ondertekening_soort: str
    ondertekening_datum: str

    integriteit_algoritme: str
    integriteit_waarde: str
    integriteit_datum: str

    informatieobjecttype: str
    zaak_id: str
    trefwoorden: str

    comment: Optional[str] = None
    succeeded: bool = False

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

    def get_inhoud(self):
        if not self.bestandspad:
            return None

        path = Path(self.bestandspad)

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

    def get_bestandsomvang(self):
        if not self.bestandsomvang:
            return None

        return int(self.bestandsomvang)

    def get_indicatie_gebruiksrecht(self):
        return self.indicatie_gebruiksrecht in ("True", "true")

    def get_ondertekening(self):
        if not any((self.ondertekening_soort, self.ondertekening_datum,)):
            return None

        return {
            "soort": self.ondertekening_soort,
            "datum": self.ondertekening_datum,
        }

    def get_integriteit(self):
        if not any(
            (
                self.integriteit_datum,
                self.integriteit_waarde,
                self.integriteit_algoritme,
            )
        ):
            return None

        return {
            "algoritme": self.integriteit_algoritme,
            "waarde": self.integriteit_waarde,
            "datum": self.integriteit_datum,
        }

    def get_trefwoorden(self):
        # TODO: remove quotes
        if not self.trefwoorden:
            return []

        return self.trefwoorden.split(",")

    def as_serializer_data(self):
        inhoud = self.get_inhoud() or None

        return {
            "identificatie": self.identificatie,
            "bronorganisatie": self.bronorganisatie or None,
            "creatiedatum": self.creatiedatum or None,
            "titel": self.titel or None,
            "vertrouwelijkheidaanduiding": self.vertrouwelijkheidaanduiding,
            "auteur": self.auteur or None,
            "status": self.status,
            "formaat": self.formaat,
            "taal": self.taal or None,
            "bestandsnaam": self.bestandsnaam,
            "inhoud": inhoud,
            "bestandsomvang": self.get_bestandsomvang(),
            "link": self.link,
            "beschrijving": self.beschrijving,
            "indicatieGebruiksrecht": self.get_indicatie_gebruiksrecht(),
            "verschijningsvorm": self.verschijningsvorm,
            "ondertekening": self.get_ondertekening(),
            "integriteit": self.get_integriteit(),
            "informatieobjecttype": self.informatieobjecttype,
            "trefwoorden": self.get_trefwoorden(),
        }

    def as_original(self):
        return {
            "identificatie": self.identificatie,
            "bronorganisatie": self.bronorganisatie,
            "creatiedatum": self.creatiedatum,
            "titel": self.titel,
            "vertrouwelijkheidaanduiding": self.vertrouwelijkheidaanduiding,
            "auteur": self.auteur,
            "status": self.status,
            "formaat": self.formaat,
            "taal": self.taal,
            "bestandsnaam": self.bestandsnaam,
            "bestandsomvang": self.bestandsomvang,
            "bestandspad": self.bestandspad,
            "link": self.link,
            "beschrijving": self.beschrijving,
            "indicatieGebruiksrecht": self.indicatie_gebruiksrecht,
            "verschijningsvorm": self.verschijningsvorm,
            "ondertekening.soort": self.ondertekening_soort,
            "ondertekening.datum": self.ondertekening_datum,
            "integriteit.algoritme": self.integriteit_algoritme,
            "integriteit.waarde": self.integriteit_waarde,
            "integriteit.datum": self.integriteit_datum,
            "informatieobjecttype": self.informatieobjecttype,
            "zaakId": self.zaak_id,
            "trefwoorden": self.trefwoorden,
        }

    def as_export_data(self):
        return {
            **self.as_original(),
            "opmerking": self.comment,
        }


def _import_document_row(
    row: list[str], row_index: int, zaak_uuids: Iterable[str]
) -> DocumentRow:
    expected_column_count = len(DocumentRow.import_headers)  # ignore the `self` arg

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

        return document_row

    try:
        import_data = document_row.as_serializer_data()
    except Exception as e:
        error_message = f"Unable to import line {row_index}: {e}"

        logger.warning(error_message)
        document_row.comment = error_message
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

        return document_row

    zaak_uuid = document_row.zaak_id

    if zaak_uuid and document_row.zaak_id not in zaak_uuids:
        error_message = f"Unknown ZAAK uuid for line {row_index}"

        logger.warning(error_message)
        document_row.comment = error_message

        return document_row

    eio = eio_serializer.save()

    if not zaak_uuid:
        document_row.succeeded = True

        return document_row

    try:
        zaak = Zaak.objects.get(uuid=zaak_uuid)
    except Zaak.DoesNotExist:
        error_message = f"Unknown ZAAK uuid for line {row_index}"

        logger.warning(error_message)
        document_row.comment = error_message

        return document_row

    zaak_informatie_object = ZaakInformatieObject(
        zaak=zaak,
        informatieobject=eio.canonical,
        aard_relatie=RelatieAarden.from_object_type("zaak"),
    )

    logger.debug(f"Validating ZAAKINFORMATIEOBJECT for eio {eio.uuid}")

    try:
        zaak_informatie_object.full_clean()
    except ValidationError as e:
        error_message = f"Validation for ZAAKINFORMATIEOBJECT failed: {e}"

        logger.warning(error_message)
        document_row.comment = error_message

        return document_row

    zaak_informatie_object.save()

    document_row.succeeded = True

    return document_row


# TODO: ensure one task is running all the time
# TODO: make this more generic?
# TODO: expose `batch_size` through API?
# TODO: wrap around transaction?
@celery_app.task
def import_documents(import_pk: int, batch_size=500) -> None:
    import_instance = Import.objects.get(pk=import_pk)  # noqa

    file_path = import_instance.import_file.path

    import_instance.total = _get_total_count(file_path)
    import_instance.save(update_fields=["total"])

    processed = 0
    fail_count = 0
    success_count = 0

    batch = []

    zaak_uuids = [str(uuid) for uuid in Zaak.objects.values_list("uuid", flat=True)]

    for row_index, row in _get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        document_row = _import_document_row(row, row_index, zaak_uuids)

        batch.append(document_row)

        if document_row.succeeded:
            success_count += 1
        else:
            fail_count += 1

        processed += 1

        if not len(batch) % batch_size == 0:
            continue

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
