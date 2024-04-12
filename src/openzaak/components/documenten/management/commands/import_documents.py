import csv
import logging
from base64 import b64encode
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIRequestFactory
from vng_api_common.constants import RelatieAarden

from openzaak.components.documenten.api import serializers
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.zaken.models.zaken import Zaak, ZaakInformatieObject
from openzaak.utils.cache import DjangoRequestsCache, requests_cache_enabled

logger = logging.getLogger(__name__)


# TODO: add import report file
# TODO: implement batch importing files
# TODO: wrap around a db transaction?
class Command(BaseCommand):
    help = "Bulk import documents from a given .csv file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--import-file",
            type=str,
            help=_(
                "The name of the .csv file to import from. Note that this file"
                " should contain all metadata needed to create "
                "EnkelvoudigInformatieObject's (EIO)."
            ),
        )

        parser.add_argument(
            "--metadata-delimiter",
            type=str,
            default=",",
            help=_("The delimiter used when parsing the metadata file."),
        )

        parser.add_argument(
            "--metadata-quotechar",
            type=str,
            default='"',
            help=_("The quote character used when parsing the metadata file."),
        )

    @requests_cache_enabled("import_documents", backend=DjangoRequestsCache())
    @transaction.atomic
    def handle(self, *args, **options):
        _import_file = options.pop("import_file")

        request_factory = APIRequestFactory()
        request = request_factory.get("/")

        logger.info("Validating import metadata file")

        # TODO: move validation to separate function call
        with open(_import_file) as import_file:
            field_names = (
                "bestandspad",
                "bronorganisatie",
                "creatiedatum",
                "titel",
                "auteur",
                "taal",
                "informatieobjecttype",
                "zaakId",
                "identificatie",
                "vertrouwelijkheidaanduiding",
                "status",
                "formaat",
                "bestandsnaam",
                "beschrijving",
                "verschijningsvorm",
            )

            blank_field_names = (
                "identificatie",
                "vertrouwelijkheidaanduiding",
                "status",
                "formaat",
                "bestandsnaam",
                "beschrijving",
                "verschijningsvorm",
            )

            csv_reader = csv.DictReader(
                import_file,
                fieldnames=field_names,
                restkey="unknown",
                delimiter=options.pop("metadata_delimiter"),
                quotechar=options.pop("metadata_quotechar"),
            )

            organisation_identifier_mapping = {}

            for row_number, row in enumerate(csv_reader, start=1):
                # Remove the `unknown` key as this contains all extra fields
                # which are not specified by `fieldnames` earlier and not known
                # by the API. Use dummy file content for validation, the actual
                # file will be imported later during the import using the
                # `bestandspad` value.
                data = {
                    **{
                        key: value
                        for key, value in row.items()
                        if key not in ["unknown", "bestandspad", "zaakId"]
                    },
                    "inhoud": b64encode(b"dummy"),
                }

                # Populate fields which may be blank
                for blank_field in blank_field_names:
                    if data[blank_field]:
                        continue

                    data[blank_field] = ""

                logger.debug(f"Validating line {row_number}")

                eio_serializer = serializers.EnkelvoudigInformatieObjectSerializer(
                    data=data, context={"request": request}
                )

                if not eio_serializer.is_valid():
                    raise CommandError(
                        _(
                            "A validation error occurred while deserializing a "
                            "EnkelvoudigInformtatieObject on line {}: \n{}"
                        ).format(row_number, eio_serializer.errors)
                    )

                if not row.get("bestandspad"):
                    errors = {
                        "bestandspad": [
                            ErrorDetail(
                                string=_("Dit veld is verplicht."), code="required"
                            )
                        ]
                    }

                    raise CommandError(
                        _(
                            "A validation error occurred while deserializing a "
                            "EnkelvoudigInformtatieObject on line {}: \n{}"
                        ).format(row_number, errors)
                    )

                file = Path(row["bestandspad"])

                if not file.is_file():
                    errors = {
                        "bestandspad": [
                            ErrorDetail(
                                string=_(
                                    "Het opgegeven bestand kon niet gevonden worden."
                                ),
                                code="pad-bestaat-niet",
                            )
                        ]
                    }

                    raise CommandError(
                        _(
                            "A validation error occurred while deserializing a "
                            "EnkelvoudigInformtatieObject on line {}: \n{}"
                        ).format(row_number, errors)
                    )

                # `identificatie` is generated when not given
                identificatie = data.get("identificatie")
                bronorganisatie = data["bronorganisatie"]
                existing_identifiers = organisation_identifier_mapping.get(
                    bronorganisatie, []
                )

                if identificatie:
                    if identificatie in existing_identifiers:
                        errors = {
                            "identificatie": [
                                ErrorDetail(
                                    string=_(
                                        "Deze identificatie bestaat al voor deze "
                                        "bronorganisatie"
                                    ),
                                    code="identificatie-niet-uniek",
                                )
                            ]
                        }

                        raise CommandError(
                            _(
                                "A validation error occurred while deserializing a "
                                "EnkelvoudigInformtatieObject on line {}: \n{}"
                            ).format(row_number, errors)
                        )

                    organisation_identifier_mapping[bronorganisatie] = [
                        *existing_identifiers,
                        identificatie,
                    ]

                canonical_eio = EnkelvoudigInformatieObjectCanonical.objects.create()
                eio_data = {**eio_serializer.validated_data, "canonical": canonical_eio}

                # No many-to-many relations will be saved during the import for
                # eio's so creating an instance like this should not cause any
                # problems.
                eio = EnkelvoudigInformatieObject.objects.create(**eio_data)

                if eio.identificatie not in existing_identifiers:
                    organisation_identifier_mapping[bronorganisatie] = [
                        *existing_identifiers,
                        eio.identificatie,
                    ]

                zaak_id = row.get("zaakId")
                zaak = None

                if zaak_id:
                    logger.debug(f"Looking up zaak {zaak_id}")

                    try:
                        zaak = Zaak.objects.get(uuid=zaak_id)

                        logger.debug(f"Zaak {zaak_id} found")
                    except (Zaak.DoesNotExist, ValidationError) as e:
                        errors = {
                            "zaakId": [
                                ErrorDetail(
                                    string=_(
                                        "The object does not exist in the database"
                                    ),
                                    code="object-does-not-exist",
                                )
                            ]
                        }

                        raise CommandError(
                            _(
                                "A validation error occurred while deserializing a "
                                "EnkelvoudigInformtatieObject on line {}: \n{}"
                            ).format(row_number, errors)
                        ) from e

                if not zaak:
                    logger.debug(f"Successfully validated line {row_number}")
                    logger.debug(f"Saving line {row_number}")
                    continue

                zaak_informatie_object = ZaakInformatieObject(
                    zaak=zaak,
                    informatieobject=canonical_eio,
                    aard_relatie=RelatieAarden.from_object_type("zaak"),
                )

                logger.debug(f"Validating zaakinformatieobject for eio {eio.uuid}")

                try:
                    zaak_informatie_object.full_clean()
                except ValidationError as e:
                    errors = {
                        "zaakinformatieobject": [
                            ErrorDetail(string=_("Object did not pass validation"),)
                        ]
                    }

                    raise CommandError(
                        _(
                            "A validation error occurred while creating a "
                            "ZaakInformatieObject for line {}: \n{}"
                        ).format(row_number, errors)
                    ) from e

                zaak_informatie_object.save()

                logger.debug(f"Successfully validated line {row_number}")
                logger.debug(f"Saving line {row_number}")
