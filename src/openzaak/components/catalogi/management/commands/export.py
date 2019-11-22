import json
import zipfile

from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.catalogi.api import serializers


class Command(BaseCommand):
    help = _("Export the objects with the ids for the specified resource as json")

    def add_arguments(self, parser):
        parser.add_argument(
            "archive_name", help=_("Name of the archive to write data to")
        )
        parser.add_argument(
            "--resource",
            "--input",
            action="append",
            nargs="*",
            help=_("Name of the resource to export objects for"),
        )
        parser.add_argument(
            "--ids",
            help=_("IDs of objects to be exported for the resource"),
            action="append",
            nargs="*",
            type=str,
        )

    def handle(self, *args, **options):
        archive_name = options.pop("archive_name")
        resources = options.pop("resource")
        ids = options.pop("ids")

        filenames = []

        for resource, id_list in zip(resources, ids):
            resource = resource[0]
            parsed_ids = [int(i) for i in id_list[0].split(",")]

            results = []

            model = apps.get_model("catalogi", resource)
            serializer = getattr(serializers, f"{resource}Serializer")
            objects = model.objects.filter(id__in=parsed_ids)

            factory = APIRequestFactory()
            request = factory.get("/")

            setattr(request, "versioning_scheme", URLPathVersioning())
            setattr(request, "version", "1")

            for instance in objects:
                serialized = serializer(instance, context={"request": request})
                data = serialized.data

                if resource == "BesluitType":
                    data["zaaktypen"] = []
                results.append(data)

            if results:
                with zipfile.ZipFile(archive_name, "a") as zip_file:
                    zip_file.writestr(f"{resource}.json", json.dumps(results))
