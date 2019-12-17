import io
import json
import zipfile

from django.core.management import CommandError
from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from ..api import serializers
from ..models import BesluitType, Catalogus, InformatieObjectType

factory = APIRequestFactory()
REQUEST = factory.get("/")
setattr(REQUEST, "versioning_scheme", URLPathVersioning())
setattr(REQUEST, "version", "1")


def retrieve_iotypen(catalogus_pk, import_file_content):
    catalogus = Catalogus.objects.get(pk=catalogus_pk)
    catalogus_uuid = str(catalogus.uuid)

    import_file = io.BytesIO(import_file_content)

    iotypen = []
    with zipfile.ZipFile(import_file, "r") as zip_file:
        if f"InformatieObjectType.json" in zip_file.namelist():
            data = zip_file.read(f"InformatieObjectType.json").decode()

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
        if f"BesluitType.json" in zip_file.namelist():
            data = zip_file.read(f"BesluitType.json").decode()

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


def construct_iotypen(iotypen, iotype_form_data):

    iotypen_uuid_mapping = {}
    for imported, form_data in zip(iotypen, iotype_form_data):
        uuid = imported["url"].split("/")[-1]
        if form_data["existing"]:
            iotypen_uuid_mapping[uuid] = form_data["existing"]
        else:
            deserialized = serializers.InformatieObjectTypeSerializer(
                data=imported, context={"request": REQUEST}
            )
            if deserialized.is_valid():
                instance = InformatieObjectType(**deserialized.validated_data)
            else:
                raise CommandError(
                    _(
                        "A validation error occurred while deserializing a {}\n{}"
                    ).format("InformatieObjectType", deserialized.errors)
                )
            instance.save()
            iotypen_uuid_mapping[uuid] = instance
    return iotypen_uuid_mapping


def construct_besluittypen(besluittypen, besluittype_form_data, iotypen_uuid_mapping):
    besluittypen_uuid_mapping = {}
    for (imported, related_iotypen_uuids,), form_data in zip(
        besluittypen, besluittype_form_data
    ):
        uuid = imported["url"].split("/")[-1]
        if form_data["existing"]:
            chosen_object = form_data["existing"]
        else:
            deserialized = serializers.BesluitTypeSerializer(
                data=imported, context={"request": REQUEST}
            )
            if deserialized.is_valid():
                deserialized.validated_data.pop("zaaktypen")
                deserialized.validated_data.pop("informatieobjecttypen")

                instance = BesluitType(**deserialized.validated_data)
            else:
                raise CommandError(
                    _(
                        "A validation error occurred while deserializing a {}\n{}"
                    ).format("BesluitType", deserialized.errors)
                )
            instance.save()
            chosen_object = instance
        besluittypen_uuid_mapping[uuid] = chosen_object

        # Recreate the BesluitType-InformatieObjectType relations
        # from the import file
        related_iotypen = [iotypen_uuid_mapping[uuid] for uuid in related_iotypen_uuids]
        chosen_object.informatieobjecttypen.set(related_iotypen)
    return besluittypen_uuid_mapping


def import_zaaktype_for_catalogus(
    catalogus_pk, import_file_content, iotypen_uuid_mapping, besluittypen_uuid_mapping
):
    catalogus = Catalogus.objects.get(pk=catalogus_pk)
    catalogus_uuid = str(catalogus.uuid)

    import_file = io.BytesIO(import_file_content)

    uuid_mapping = {}

    with zipfile.ZipFile(import_file, "r") as zip_file:
        for resource in [
            "ZaakType",
            "ZaakTypeInformatieObjectType",
            "ResultaatType",
            "RolType",
            "StatusType",
            "Eigenschap",
        ]:
            if f"{resource}.json" in zip_file.namelist():
                data = zip_file.read(f"{resource}.json").decode()

                if resource == "ZaakTypeInformatieObjectType":
                    for old, new in iotypen_uuid_mapping.items():
                        data = data.replace(old, str(new.uuid))
                elif resource == "ZaakType":
                    for old, new in besluittypen_uuid_mapping.items():
                        data = data.replace(old, str(new.uuid))

                for old, new in uuid_mapping.items():
                    data = data.replace(old, new)

                data = json.loads(data)

                serializer = getattr(serializers, f"{resource}Serializer")

                for entry in data:
                    if resource == "ZaakType":
                        entry["informatieobjecttypen"] = []
                        old_catalogus_uuid = entry["catalogus"].split("/")[-1]
                        entry["catalogus"] = entry["catalogus"].replace(
                            old_catalogus_uuid, catalogus_uuid
                        )

                    deserialized = serializer(data=entry, context={"request": REQUEST})

                    if deserialized.is_valid():
                        deserialized.save()
                        instance = deserialized.instance
                        uuid_mapping[entry["url"].split("/")[-1]] = str(instance.uuid)
                    else:
                        raise CommandError(
                            _(
                                "A validation error occurred while deserializing a {}\n{}"
                            ).format(resource, deserialized.errors)
                        )
