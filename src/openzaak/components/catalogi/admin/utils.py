# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import io
import json
import zipfile

from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ngettext

from dateutil.relativedelta import relativedelta
from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.utils.cache import requests_cache_enabled

from ..api import serializers
from ..models import BesluitType, Catalogus, InformatieObjectType

factory = APIRequestFactory()
REQUEST = factory.get("/")
setattr(REQUEST, "versioning_scheme", URLPathVersioning())
setattr(REQUEST, "version", "1")


def format_serializer_errors(errors, related=False):
    """
    Formats a DRF serializer's validation errors to a single string
    :param errors: standard DRF error dict returned from a serializer
    :param related: whether an error dict is from a related serializer
    :returns: errors formatted as a string
    """

    # if list of errors
    if isinstance(errors, list):
        return ",".join([f"{error.title()}" for error in errors])

    seperator = ", " if related else "\n"
    # otherwise nested error list
    return seperator.join(
        [f"{k}: {format_serializer_errors(v, True)}" for k, v in errors.items()]
    )


def retrieve_iotypen(catalogus_pk, import_file_content):
    catalogus = Catalogus.objects.get(pk=catalogus_pk)
    catalogus_uuid = str(catalogus.uuid)

    import_file = io.BytesIO(import_file_content)

    iotypen = []
    with zipfile.ZipFile(import_file, "r") as zip_file:
        if "InformatieObjectType.json" in zip_file.namelist():
            data = zip_file.read("InformatieObjectType.json").decode()

            data = json.loads(data)

            for entry in data:
                old_catalogus_uuid = entry["catalogus"].split("/")[-1]
                entry["catalogus"] = entry["catalogus"].replace(
                    old_catalogus_uuid, catalogus_uuid
                )
                iotypen.append(entry)
    return iotypen


def retrieve_besluittypen(catalogus_pk, import_file_content):
    catalogus = Catalogus.objects.get(pk=catalogus_pk)
    catalogus_uuid = str(catalogus.uuid)

    import_file = io.BytesIO(import_file_content)

    besluittypen = []
    with zipfile.ZipFile(import_file, "r") as zip_file:
        if "BesluitType.json" in zip_file.namelist():
            data = zip_file.read("BesluitType.json").decode()

            data = json.loads(data)

            for entry in data:
                old_catalogus_uuid = entry["catalogus"].split("/")[-1]
                entry["catalogus"] = entry["catalogus"].replace(
                    old_catalogus_uuid, catalogus_uuid
                )

                entry["zaaktypen"] = []

                # Since the InformatieObjectTypen are not created yet, the
                # UUIDs have to be stored and the relations have to be created
                # later
                related_iotypen_uuids = [
                    iotype.split("/")[-1] for iotype in entry["informatieobjecttypen"]
                ]
                entry["informatieobjecttypen"] = []

                besluittypen.append((entry, related_iotypen_uuids))
    return besluittypen


def construct_iotypen(iotypen, iotype_form_data, iot_formset, generate_new_uuids):
    iotypen_uuid_mapping = {}
    for imported, form_data, form in zip(iotypen, iotype_form_data, iot_formset.forms):
        uuid = imported["url"].split("/")[-1]
        if form_data["existing"]:
            iotypen_uuid_mapping[uuid] = form_data["existing"]
        else:
            deserialized = serializers.InformatieObjectTypeSerializer(
                data=imported, context={"request": REQUEST}
            )
            if deserialized.is_valid():
                data = deserialized.validated_data
                # process gegevens group
                omschrijving_generiek = data.pop("omschrijving_generiek", {})
                instance = InformatieObjectType(**data)
                instance.omschrijving_generiek = omschrijving_generiek
            else:
                error_message = format_serializer_errors(deserialized.errors)
                form.add_error("existing", error_message)
                raise CommandError(
                    _(
                        "A validation error occurred while deserializing a {}\n{}"
                    ).format("InformatieObjectType", error_message)
                )
            if not generate_new_uuids:
                instance.uuid = uuid
            instance.save()
            iotypen_uuid_mapping[uuid] = instance
    return iotypen_uuid_mapping


def construct_besluittypen(
    besluittypen,
    besluittype_form_data,
    iotypen_uuid_mapping,
    besluittype_formset,
    generate_new_uuids,
):
    besluittypen_uuid_mapping = {}
    for (
        (
            imported,
            related_iotypen_uuids,
        ),
        form_data,
        form,
    ) in zip(besluittypen, besluittype_form_data, besluittype_formset):
        uuid = imported["url"].split("/")[-1]
        if form_data["existing"]:
            chosen_object = form_data["existing"]
        else:
            deserialized = serializers.BesluitTypeSerializer(
                data=imported, context={"request": REQUEST}
            )
            if deserialized.is_valid():
                deserialized.validated_data.pop("informatieobjecttypen")

                instance = BesluitType(**deserialized.validated_data)
            else:
                error_message = format_serializer_errors(deserialized.errors)
                form.add_error("existing", error_message)
                raise CommandError(
                    _(
                        "A validation error occurred while deserializing a {}\n{}"
                    ).format("BesluitType", error_message)
                )
            if not generate_new_uuids:
                instance.uuid = uuid
            instance.save()
            chosen_object = instance
        besluittypen_uuid_mapping[uuid] = chosen_object

        # Recreate the BesluitType-InformatieObjectType relations
        # from the import file
        related_iotypen = [iotypen_uuid_mapping[uuid] for uuid in related_iotypen_uuids]
        chosen_object.informatieobjecttypen.set(related_iotypen)
    return besluittypen_uuid_mapping


@requests_cache_enabled()
def import_zaaktype_for_catalogus(
    identificatie_prefix,
    catalogus_pk,
    import_file_content,
    iotypen_uuid_mapping,
    besluittypen_uuid_mapping,
    generate_new_uuids,
):
    catalogus = Catalogus.objects.get(pk=catalogus_pk)
    catalogus_uuid = str(catalogus.uuid)

    import_file = io.BytesIO(import_file_content)

    uuid_mapping = {}

    files_not_found = []
    files_found = []

    with zipfile.ZipFile(import_file, "r") as zip_file:

        files_received = zip_file.namelist()
        for resource in [
            "ZaakType",
            "ZaakTypeInformatieObjectType",
            "ResultaatType",
            "RolType",
            "StatusType",
            "Eigenschap",
        ]:
            if f"{resource}.json" in files_received:
                data = zip_file.read(f"{resource}.json").decode()
                files_found.append(f"{resource}.json")

                # These mappings are also needed when `generate_new_uuids=False`, because
                # it is possible to select existing InformatieObjectTypen/BesluitTypen
                # to link a ZaakType to, which may have different UUIDs than those in
                # the import file (possibly because they are newer version)
                if resource == "ZaakTypeInformatieObjectType":
                    for old, new in iotypen_uuid_mapping.items():
                        data = data.replace(old, str(new.uuid))
                elif resource == "ZaakType":
                    for old, new in besluittypen_uuid_mapping.items():
                        data = data.replace(old, str(new.uuid))

                if generate_new_uuids:
                    for old, new in uuid_mapping.items():
                        data = data.replace(old, new)

                data = json.loads(data)

                serializer = getattr(serializers, f"{resource}Serializer")

                for entry in data:
                    if resource == "ZaakType":
                        if identificatie_prefix:

                            new_identification = (
                                f"{identificatie_prefix}_{entry['identificatie']}"
                            )

                            if len(new_identification) > 50:
                                raise ValidationError(
                                    _(
                                        "Identification {} is too long with prefix. Max 50 characters."
                                    ).format(new_identification)
                                )

                            entry["identificatie"] = new_identification

                        entry["informatieobjecttypen"] = []
                        old_catalogus_uuid = entry["catalogus"].split("/")[-1]
                        entry["catalogus"] = entry["catalogus"].replace(
                            old_catalogus_uuid, catalogus_uuid
                        )

                    deserialized = serializer(data=entry, context={"request": REQUEST})

                    if deserialized.is_valid():
                        if generate_new_uuids:
                            deserialized.save()
                            instance = deserialized.instance
                            uuid_mapping[entry["url"].split("/")[-1]] = str(
                                instance.uuid
                            )
                        else:
                            deserialized.save(uuid=entry["url"].split("/")[-1])
                    else:
                        raise CommandError(
                            _(
                                "A validation error occurred while deserializing a {}\n{}"
                            ).format(resource, deserialized.errors)
                        )
            else:
                files_not_found.append(f"{resource}.json")

    if len(files_found) < 1:
        msg = _(
            "No files found. Expected: {files_not_found} but received:<br> {files_received}"
        )
        msg_dict = {
            "files_not_found": ", ".join(files_not_found),
            "files_received": ", ".join(files_received),
        }

        raise CommandError(format_html(msg, **msg_dict))


def format_duration(rel_delta: relativedelta) -> str:
    """
    convert relativedelta object into human-readable string
    """
    bits = []

    if rel_delta.years:
        bits.append(
            ngettext(
                "{years} year",
                "{years} years",
                rel_delta.years,
            ).format(years=rel_delta.years)
        )

    if rel_delta.months:
        bits.append(
            ngettext(
                "{months} month",
                "{months} months",
                rel_delta.months,
            ).format(months=rel_delta.months)
        )

    if rel_delta.days:
        bits.append(
            ngettext(
                "{days} day",
                "{days} days",
                rel_delta.days,
            ).format(days=rel_delta.days)
        )

    if rel_delta.hours:
        bits.append(
            ngettext(
                "{hours} hour",
                "{hours} hours",
                rel_delta.hours,
            ).format(hours=rel_delta.hours)
        )

    if rel_delta.minutes:
        bits.append(
            ngettext(
                "{minutes} minute",
                "{minutes} minutes",
                rel_delta.minutes,
            ).format(minutes=rel_delta.minutes)
        )

    if rel_delta.seconds:
        bits.append(
            ngettext(
                "{seconds} second",
                "{seconds} seconds",
                rel_delta.seconds,
            ).format(seconds=rel_delta.seconds)
        )

    if not bits:
        return "-"

    if len(bits) == 1:
        return bits[0]

    last = bits[-1]
    first = ", ".join(bits[:-1])
    return _("{first} and {last}").format(first=first, last=last)
