import csv
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import Error as DatabaseError, IntegrityError, transaction
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
from openzaak.import_data.models import (
    Import,
    ImportRowResultChoices,
    ImportStatusChoices,
)
from openzaak.import_data.utils import finish_batch, finish_import, get_csv_generator, get_total_count, task_locker
from openzaak.utils.fields import get_default_path

logger = logging.getLogger(__name__)


@dataclass
class DocumentRow:
    _uuid: str
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
    _ontvangstdatum: str
    _verzenddatum: str
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
            "uuid",
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
            "ontvangstdatum",
            "verzenddatum",
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
    def uuid(self) -> str:
        if self.instance and self.instance.uuid:
            return str(self.instance.uuid)
        return self._uuid

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
    def ontvangstdatum(self) -> Optional[str]:
        return self._ontvangstdatum or None

    @property
    def verzenddatum(self) -> Optional[str]:
        return self._verzenddatum or None

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
            "ontvangstdatum": self.ontvangstdatum,
            "verzenddatum": self.verzenddatum,
            "indicatie_gebruiksrecht": self.indicatie_gebruiksrecht,
            "verschijningsvorm": self._verschijningsvorm,
            "ondertekening": self.ondertekening,
            "integriteit": self.integriteit,
            "informatieobjecttype": self._informatieobjecttype,
            "trefwoorden": self.trefwoorden,
        }

    def as_original(self):
        return {
            "uuid": self._uuid,
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
            "ontvangstdatum": self._ontvangstdatum,
            "verzenddatum": self._verzenddatum,
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
            "uuid": self.uuid,
            "opmerking": self.comment,
            "resultaat": self.result,
        }


def _import_document_row(
    row: list[str],
    row_index: int,
    existing_uuids: list[str],
    zaak_uuids: dict[str, int],
) -> DocumentRow:
    expected_column_count = len(DocumentRow.import_headers)

    request_factory = APIRequestFactory()
    request = request_factory.get("/")

    if len(row) < expected_column_count:
        error_message = (
            f"Validation failed for line {row_index}: insufficient row count"
        )

        logger.warning(error_message)

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
            f"EnkelvoudigInformatieObject on line {row_index}: \n"
            f"{eio_serializer.errors}"
        )

        logger.warning(error_message)
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

            logger.warning(error_message)
            document_row.comment = error_message
            document_row.processed = True

            return document_row

        if document_row.uuid in existing_uuids:
            error_message = (
                f"UUID given on row {row_index} was already found! Not overwriting "
                "existing EIO."
            )

            logger.warning(error_message)
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
        instance.identificatie = generate_unique_identification(
            instance, "creatiedatum"
        )

    zaak_id = document_row.zaak_id

    if zaak_id and zaak_id not in zaak_uuids:
        error_message = f"Zaak ID specified for row {row_index} is unknown."

        logger.warning(error_message)
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

        logger.warning(error_message)
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

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    default_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
    import_path = default_dir / path.name

    if not default_dir.exists():
        default_dir.mkdir(parents=True)

    try:
        shutil.copy2(path, import_path)
    except Exception as e:
        error_message = f"Unable to copy file for row {row_index}: \n {str(e)}"

        logger.warning(error_message)
        document_row.comment = error_message
        document_row.processed = True

        return document_row

    instance.inhoud.name = str(import_path)

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
                for eio in eios if row.instance and str(eio.uuid) == str(row.instance.uuid)
            ),
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
        except DatabaseError as e:
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


# TODO: make this more generic?
@celery_app.task(bind=True)
@task_locker
def import_documents(self, import_pk: int) -> None:
    import_instance = Import.objects.get(pk=import_pk)

    file_path = import_instance.import_file.path

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

    for row_index, row in get_csv_generator(file_path):
        if row_index == 1:  # skip the header row
            continue

        if len(batch) % batch_size == 0:
            logger.info(
                f"Starting batch {import_instance.get_batch_number(batch_size)}"
            )

        document_row = _import_document_row(
            row,
            row_index,
            eio_uuids,
            zaak_uuids
        )

        if document_row.instance and document_row.instance.uuid:
            eio_uuids.append(str(document_row.instance.uuid))

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
                "An Integrity error occured during batch "
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
                "A critical error occured during batch "
                f"{import_instance.get_batch_number(batch_size)}. "
                f"Finishing import due to database error: \n{str(e)}"
            )
            logger.info("Trying to stop the import process gracefully")

            finish_batch(import_instance, batch, DocumentRow.export_headers)
            finish_import(
                import_instance, status=ImportStatusChoices.error, comment=str(e),
            )

            return

        finish_batch(import_instance, batch, DocumentRow.export_headers)

        remaining_batches = import_instance.get_remaining_batches(batch_size)
        logger.info(f"{remaining_batches} batches remaining")

        batch.clear()

    finish_import(import_instance, ImportStatusChoices.finished)
