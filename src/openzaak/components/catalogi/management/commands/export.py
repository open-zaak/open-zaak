# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import io
import json
import zipfile

from django.apps import apps
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from rest_framework.test import APIRequestFactory
from rest_framework.versioning import URLPathVersioning

from openzaak.components.catalogi.api import serializers


class Command(BaseCommand):
    help = "Export the objects with the ids for the specified resource as json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--archive_name", help=_("Name of the archive to write data to"), type=str
        )
        parser.add_argument(
            "--response",
            help=_("HttpResponse object to which the output data should be written"),
            type=HttpResponse,
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
        response = options.pop("response")

        if response and archive_name:
            raise CommandError(
                _("Please use either the --archive_name or --response argument")
            )

        all_resources = options.pop("resource")
        all_ids = options.pop("ids")

        if len(all_resources) != len(all_ids):
            raise CommandError(
                _("The number of resources supplied does not match the number of IDs")
            )

        factory = APIRequestFactory()
        server_name = Site.objects.get_current().domain
        request = factory.get("/", SERVER_NAME=server_name)
        setattr(request, "versioning_scheme", URLPathVersioning())
        setattr(request, "version", "1")

        results = []

        for resource, ids in zip(all_resources, all_ids):
            model = apps.get_model("catalogi", resource)
            serializer = getattr(serializers, f"{resource}Serializer")
            objects = model.objects.filter(id__in=ids)

            serialized = serializer(
                instance=objects, many=True, context={"request": request}
            )
            data = serialized.data

            # Because BesluitType is imported before ZaakType, related
            # ZaakTypen do not exist yet at the time of importing, so the
            # relations will be left empty when importing BesluitTypen and
            # they will be set when importing ZaakTypen
            if resource == "BesluitType":
                for entry in data:
                    entry["zaaktypen"] = []

            if data:
                results.append((resource, data))

        if response:
            f = io.BytesIO()
            for resource, data in results:
                with zipfile.ZipFile(f, "a") as zip_file:
                    zip_file.writestr(f"{resource}.json", json.dumps(data))
            response.content = f.getvalue()
        else:
            for resource, data in results:
                with zipfile.ZipFile(archive_name, "a") as zip_file:
                    zip_file.writestr(f"{resource}.json", json.dumps(data))
