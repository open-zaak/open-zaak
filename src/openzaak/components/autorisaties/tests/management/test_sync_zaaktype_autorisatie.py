# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase

from vng_api_common.authorizations.models import Autorisatie

from openzaak.components.autorisaties.tests.factories import AutorisatieFactory
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils import build_absolute_url


class ZaaktypeSyncAutorisatieTests(TestCase):
    def test_management_sync_autorisatie_delete_all(self):
        domain = Site.objects.get_current().domain
        # Create 5 Autorisaties for non existing ZaakTypen
        for i in range(5):
            AutorisatieFactory.create(
                zaaktype=f"http://{domain}/catalogi/api/v1/zaaktypen/{str(uuid.uuid4())}",
            )

        self.assertEqual(Autorisatie.objects.all().count(), 5)

        call_command("sync_autorisaties")

        self.assertEqual(Autorisatie.objects.all().count(), 0)

    def test_management_sync_autorisatie_delete_some(self):
        domain = Site.objects.get_current().domain
        # Create 5 Autorisaties for non existing ZaakTypen
        for i in range(5):
            AutorisatieFactory.create(
                zaaktype=f"http://{domain}/catalogi/api/v1/zaaktypen/{str(uuid.uuid4())}",
            )

        # Add an Autorisatie for an existing Zaaktype
        zaaktype = ZaakTypeFactory.create()
        AutorisatieFactory.create(
            zaaktype=build_absolute_url(zaaktype.get_absolute_api_url()),
        )

        self.assertEqual(Autorisatie.objects.all().count(), 6)

        call_command("sync_autorisaties")

        self.assertEqual(Autorisatie.objects.all().count(), 1)
        autorisatie = Autorisatie.objects.get()
        self.assertEqual(
            autorisatie.zaaktype, build_absolute_url(zaaktype.get_absolute_api_url())
        )
