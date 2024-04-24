import csv
import logging
from dataclasses import dataclass
from inspect import getfullargspec
from pathlib import Path
from typing import Generator

from django.core.exceptions import ValidationError

from rest_framework.test import APIRequestFactory
from vng_api_common.constants import RelatieAarden

from openzaak import celery_app
from openzaak.components.documenten.api.serializers import (
    EnkelvoudigInformatieObjectSerializer,
)
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.zaken.models.zaken import Zaak, ZaakInformatieObject
from openzaak.utils.models import Import

logger = logging.getLogger(__name__)


def get_csv_generator(filename: str) -> Generator[tuple[int, list], None, None]:
    with open(filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')

        index = 1

        for row in csv_reader:
            yield index, row

            index += 1


def get_total_count(filename: str) -> int:
    with open(filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        total = sum(1 for _ in csv_reader)

        return total - 1 if total > 0 else 0  # don't count the header row


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

    def get_inhoud(self):
        if not self.bestandspad:
            return None

        path = Path(self.bestandspad)

        if not path.exists() or not path.is_file():
            raise IOError("The given filepath does not exist or is not a file.")

        with open(path, "rb") as import_file:
            file_contents = import_file.read()
            import_file.seek(0)

        return file_contents

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
        if not self.trefwoorden:
            return []

        return self.trefwoorden.split(",")

    def as_serializer_data(self):
        # Note that `inhoud` is not included here as files probably are not base64
        # encoded (which the API expects). File contents will be read and saved
        # after validating.
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

    def as_import_data(self):
        data = self.as_serializer_data()

        return {**data, "inhoud": self.get_inhoud()}

    def as_export_data(self):
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
            "trefwoorden": self.trefwoorden,
            "opmerking": self.comment,
        }

    def set_import_comment(self, comment: str):
        self.comment = comment


# TODO: ensure one task is running all the time
# TODO: make this more generic?
# TODO: split into seperate function (outside of celery task)
# TODO: wrap around transaction?
@celery_app.task
def import_documents(import_pk: int, batch_size=500) -> None:
    import_instance = Import.objects.get(pk=import_pk)  # noqa

    document_args = getfullargspec(DocumentRow.__init__)
    expected_column_count = len(document_args.args[1:])  # ignore the `self` arg

    request_factory = APIRequestFactory()
    request = request_factory.get("/")

    file_path = import_instance.import_file.path

    import_instance.total = get_total_count(file_path)
    import_instance.save(update_fields=["total"])

    processed = 0
    fail_count = 0
    success_count = 0

    batch = []

    zaak_uuids = Zaak.objects.values_list("uuid", flat=True)

    for row_index, row in get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        logger.debug(f"Validating line {row_index}")

        # TODO: is this possible with an invalid row count?
        document_row = DocumentRow(*row[:expected_column_count])

        if len(row) < expected_column_count:
            error_message = (
                f"Validation failed for line {row_index}: insufficient row count."
            )

            logger.warning(error_message)
            document_row.set_import_comment(error_message)

            batch.append(document_row)

            processed += 1
            fail_count += 1
            continue

        eio_serializer = EnkelvoudigInformatieObjectSerializer(
            data=document_row.as_serializer_data(), context={"request": request}
        )

        if not eio_serializer.is_valid():
            error_message = (
                "A validation error occurred while deserializing a "
                "EnkelvoudigInformtatieObject on line %(row_index)s: \n"
                "%(errors)s"
            ) % dict(row_index=row_index, errors=eio_serializer.errors)

            logger.debug(error_message)
            document_row.set_import_comment(error_message)

            batch.append(document_row)

            processed += 1
            fail_count += 1
            continue

        try:
            import_data = document_row.as_import_data()
        except Exception as e:
            error_message = f"Failed importing line {row_index}: \n{e}"

            logger.warning(error_message)
            document_row.set_import_comment(error_message)

            batch.append(document_row)

            processed += 1
            fail_count += 1
            continue

        if document_row.zaak_id and document_row.zaak_id not in zaak_uuids:
            error_message = f"Unknown ZAAK uuid for line {row_index}"

            logger.warning(error_message)
            document_row.set_import_comment(error_message)

            batch.append(document_row)

            processed += 1
            fail_count += 1
            continue

        canonical_eio = EnkelvoudigInformatieObjectCanonical.objects.create()
        eio_data = {**import_data, "canonical": canonical_eio}

        # No many-to-many relations will be saved during the import for
        # eio's so creating an instance like this should not cause any
        # problems.
        eio = EnkelvoudigInformatieObject.objects.create(**eio_data)

        if document_row.zaak_id:
            zaak = Zaak.objects.get(uuid=document_row.zaak_id)
            zaak_informatie_object = ZaakInformatieObject(
                zaak=zaak,
                informatieobject=canonical_eio,
                aard_relatie=RelatieAarden.from_object_type("zaak"),
            )

            logger.debug(f"Validating ZAAKINFORMATIEOBJECT for eio {eio.uuid}")

            try:
                zaak_informatie_object.full_clean()
            except ValidationError as e:
                error_message = f"Validation for ZAAKINFORMATIEOBJECT failed: {e}"

                logger.warning(error_message)
                batch.append(document_row)

                processed += 1
                fail_count += 1
                continue

            zaak_informatie_object.save()

        batch.append(document_row)
        success_count += 1
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
