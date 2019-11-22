import json
import zipfile

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.catalogi.api import serializers

IMPORT_ORDER = [
    "Catalogus",
    "InformatieObjectType",
    "BesluitType",
    "ZaakType",
    "ZaakInformatieobjectType",
    "ResultaatType",
    "RolType",
    "StatusType",
    "Eigenschap",
]


class Command(BaseCommand):
    help = _("Import Catalogi data from a .zip file")

    def add_arguments(self, parser):
        parser.add_argument(
            "import_file", type=str, help=_("Name of the .zip file to import from")
        )

    @transaction.atomic
    def handle(self, *args, **options):
        import_file = options.pop("import_file")
        uuid_mapping = {}

        with zipfile.ZipFile(import_file, "r") as zip_file:
            for resource in IMPORT_ORDER:
                if f"{resource}.json" in zip_file.namelist():
                    data = zip_file.read(f"{resource}.json").decode()
                    for old, new in uuid_mapping.items():
                        data = data.replace(old, new)

                    data = json.loads(data)

                    model = apps.get_model("catalogi", resource)
                    serializer = getattr(serializers, f"{resource}Serializer")

                    factory = APIRequestFactory()
                    request = factory.get("/")

                    setattr(request, "versioning_scheme", URLPathVersioning())
                    setattr(request, "version", "1")

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
                                    f"A validation error occurred while deserializing a {resource}\n{deserialized.errors}"
                                )
                            )
