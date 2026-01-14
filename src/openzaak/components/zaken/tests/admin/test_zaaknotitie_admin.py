# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.notes.constants import NotitieStatus, NotitieType

from openzaak.components.zaken.models import ZaakNotitie
from openzaak.tests.utils import AdminTestMixin

from ..factories import ZaakFactory, ZaakNotitieFactory


@disable_admin_mfa()
class ZaakNotitieAdminTests(AdminTestMixin, WebTest):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_valid_create_zaaknotitie(self):
        zaak = ZaakFactory.create()

        get_response = self.app.get(reverse("admin:zaken_zaaknotitie_add"))
        form = get_response.forms["zaaknotitie_form"]
        form["gerelateerd_aan"] = zaak.id
        form["onderwerp"] = "onderwerp"
        form["tekst"] = "tekst"
        form["aangemaakt_door"] = "aangemaakt_door"
        form["notitie_type"] = NotitieType.INTERN
        form["status"] = NotitieStatus.CONCEPT

        form.submit()

        self.assertEqual(ZaakNotitie.objects.count(), 1)
        zaaknotitie = ZaakNotitie.objects.get()

        self.assertEqual(zaaknotitie.gerelateerd_aan.id, zaak.id)
        self.assertEqual(zaaknotitie.onderwerp, "onderwerp")
        self.assertEqual(zaaknotitie.tekst, "tekst")
        self.assertEqual(zaaknotitie.aangemaakt_door, "aangemaakt_door")
        self.assertEqual(zaaknotitie.notitie_type, NotitieType.INTERN)
        self.assertEqual(zaaknotitie.status, NotitieStatus.CONCEPT)

    def test_invalid_create_zaaknotitie(self):
        zaak = ZaakFactory.create()

        get_response = self.app.get(reverse("admin:zaken_zaaknotitie_add"))
        form = get_response.forms["zaaknotitie_form"]
        form["gerelateerd_aan"] = zaak.id
        form["tekst"] = "tekst"
        form["aangemaakt_door"] = "aangemaakt_door"
        form["notitie_type"] = NotitieType.INTERN
        form["status"] = NotitieStatus.CONCEPT

        response = form.submit()
        self.assertContains(
            response,
            "Dit veld is verplicht.",  # onderwerp field
        )
        self.assertEqual(ZaakNotitie.objects.count(), 0)

    def test_valid_update_zaaknotitie(self):
        zaak = ZaakFactory.create()
        zaaknotitie = ZaakNotitieFactory.create(
            gerelateerd_aan=zaak,
            onderwerp="test_onderwerp",
            tekst="test",
            status=NotitieStatus.CONCEPT.value,
            notitie_type=NotitieType.INTERN.value,
        )
        get_response = self.app.get(
            reverse("admin:zaken_zaaknotitie_change", args=(zaaknotitie.pk,))
        )

        form = get_response.forms["zaaknotitie_form"]
        form["notitie_type"] = NotitieType.EXTERN
        form["status"] = NotitieStatus.DEFINITIEF

        form.submit()

        self.assertEqual(ZaakNotitie.objects.count(), 1)
        zaaknotitie = ZaakNotitie.objects.get()

        self.assertEqual(zaaknotitie.gerelateerd_aan.id, zaak.id)
        self.assertEqual(zaaknotitie.onderwerp, "test_onderwerp")
        self.assertEqual(zaaknotitie.tekst, "test")
        self.assertEqual(zaaknotitie.notitie_type, NotitieType.EXTERN)
        self.assertEqual(zaaknotitie.status, NotitieStatus.DEFINITIEF)
