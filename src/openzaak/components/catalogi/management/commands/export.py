import json
import zipfile

from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.catalogi.api import serializers


class Command(BaseCommand):
    help = "Export the objects with the ids for the specified resource as json"

    def add_arguments(self, parser):
        parser.add_argument(
            "archive_name", help=_("Name of the archive to write data to")
        )
        parser.add_argument(
            "--resource",
            action="append",
            type=str,
            help=_("Name of the resource to export objects for"),
        )
        parser.add_argument(
            "--ids",
            help=_("IDs of objects to be exported for the resource"),
            action="append",
            nargs="*",
            type=int,
        )

    def handle(self, *args, **options):
        archive_name = options.pop("archive_name")
        all_resources = options.pop("resource")
        all_ids = options.pop("ids")

        filenames = []

        factory = APIRequestFactory()
        request = factory.get("/")
        setattr(request, "versioning_scheme", URLPathVersioning())
        setattr(request, "version", "1")

        for resource, ids in zip(all_resources, all_ids):
            model = apps.get_model("catalogi", resource)
            serializer = getattr(serializers, f"{resource}Serializer")
            objects = model.objects.filter(id__in=ids)

            serialized = serializer(
                instance=objects, many=True, context={"request": request}
            )
            results = serialized.data

            # Because BesluitType is imported before ZaakType, related
            # ZaakTypen do not exist yet at the time of importing, so the
            # relations will be left empty when importing BesluitTypen and
            # they will be set when importing ZaakTypen
            if resource == "BesluitType":
                for data in results:
                    data["zaaktypen"] = []

            if results:
                with zipfile.ZipFile(archive_name, "a") as zip_file:
                    zip_file.writestr(f"{resource}.json", json.dumps(results))
