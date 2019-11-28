import json
import io
import zipfile

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile

from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.catalogi.api import serializers

IMPORT_ORDER = [
    "Catalogus",
    "InformatieObjectType",
    "BesluitType",
    "ZaakType",
    "ZaakTypeInformatieObjectType",
    "ResultaatType",
    "RolType",
    "StatusType",
    "Eigenschap",
]


class Command(BaseCommand):
    help = "Import Catalogi data from a .zip file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--import_file", type=str, help=_("The name of the .zip file to import from")
        )
        parser.add_argument(
            "--import_file_content", type=bytes, help=_("The .zip file content to import from")
        )

    @transaction.atomic
    def handle(self, *args, **options):
        import_file = options.pop("import_file")
        import_file_content = options.pop("import_file_content")

        if import_file and import_file_content:
            raise CommandError(_("Please use either the --import_file or --import_file_content argument"))

        if import_file_content:
            import_file = io.BytesIO(import_file_content)

        uuid_mapping = {}

        factory = APIRequestFactory()
        request = factory.get("/")
        setattr(request, "versioning_scheme", URLPathVersioning())
        setattr(request, "version", "1")

        with zipfile.ZipFile(import_file, "r") as zip_file:
            for resource in IMPORT_ORDER:
                if f"{resource}.json" in zip_file.namelist():
                    data = zip_file.read(f"{resource}.json").decode()
                    for old, new in uuid_mapping.items():
                        data = data.replace(old, new)

                    data = json.loads(data)

                    model = apps.get_model("catalogi", resource)
                    serializer = getattr(serializers, f"{resource}Serializer")

                    for entry in data:
                        deserialized = serializer(
                            data=entry, context={"request": request}
                        )

                        if deserialized.is_valid():
                            deserialized.save()
                            uuid_mapping[entry["url"].split("/")[-1]] = str(
                                deserialized.instance.uuid
                            )
                        else:
                            raise CommandError(
                                _(
                                    "A validation error occurred while deserializing a {}\n{}"
                                ).format(resource, deserialized.errors)
                            )
