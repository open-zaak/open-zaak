# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.urls import reverse

import requests
from zds_client.auth import ClientAuth


class Command(BaseCommand):
    help = "Create a test zaaktype as an integration test for OZ and ON"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--keep-data",
            dest="keep_data",
            action="store_true",
            help="The component name to define urlconf and schema info",
        )

    def handle(self, **options):
        if not settings.DEMO_CLIENT_ID or not settings.DEMO_SECRET:
            raise CommandError(
                "DEMO_CLIENT_ID and DEMO_SECRET env vars should be configured"
            )

        auth = ClientAuth(
            client_id=settings.DEMO_CLIENT_ID, secret=settings.DEMO_SECRET,
        )
        req = requests.session()
        req.headers.update({**auth.credentials(), "Accept": "application/json"})
        req.hooks = {"response": [lambda r, *args, **kwargs: r.raise_for_status()]}

        # 1. create or retrieve catalog with domein = DEMO
        # NOTE: we can't remove catalog using restful api, so it should be done manually
        catalog_list_url = reverse("catalogus-list", kwargs={"version": "1"})
        catalog_list_url = f"http://localhost:8000{catalog_list_url}"
        response = req.get(catalog_list_url, params={"domein": "DEMO"})

        result = response.json()
        if result["count"] == 1:
            catalog_url = result["results"][0]["url"]
            self.stdout.write(f"Demo catalog {catalog_url} was retrieved")
        else:
            # no demo catalog - create one
            catalog_data = {
                "domein": "DEMO",
                "contactpersoonBeheerTelefoonnummer": "0612345679",
                "rsin": "100000009",
                "contactpersoonBeheerNaam": "demo",
                "contactpersoonBeheerEmailadres": "demo@demo.com",
            }
            response = req.post(catalog_list_url, json=catalog_data)

            catalog_url = response.json()["url"]
            self.stdout.write(f"Demo catalog {catalog_url} was created")

        # 2. create or retrieve demo zaaktype
        zaaktype_list_url = reverse("zaaktype-list", kwargs={"version": "1"})
        zaaktype_list_url = f"http://localhost:8000{zaaktype_list_url}"
        zaaktype_data = {
            "identificatie": "DEMO",
            "doel": "smoke test",
            "aanleiding": "demo",
            "indicatieInternOfExtern": "extern",
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": [],
            "vertrouwelijkheidaanduiding": "openbaar",
            "omschrijving": "demo zaaktype",
            "gerelateerdeZaaktypen": [],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": catalog_url,
            "besluittypen": [],
            "beginGeldigheid": "2023-01-01",
            "versiedatum": "2023-01-01",
            "verantwoordelijke": "063308836",
        }
        response = req.post(zaaktype_list_url, json=zaaktype_data)

        zaaktype_url = response.json()["url"]
        self.stdout.write(f"Demo zaaktype {zaaktype_url} was created")

        if options["keep_data"]:
            self.stdout.write("Demo zaaktype is remained in DB")
            return

        # 3. Delete demo zaaktype
        req.delete(zaaktype_url)
        self.stdout.write(f"Demo zaaktype {zaaktype_url} was deleted")
        self.stdout.write(
            self.style.WARNING("Remove demo catalog manually in the admin")
        )
        self.stdout.write(self.style.SUCCESS("Demo process is finished"))
